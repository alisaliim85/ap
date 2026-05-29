# notifications/views.py
import uuid as _uuid
from datetime import datetime, timezone as dt_timezone

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.db import models as db_models
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.decorators.http import require_POST

from accounts.models import User
from .models import Message, Notification
from .services import NotificationService


# ── HTMX Partial Views ──────────────────────────────────────────────────────

@login_required
def unread_count(request):
    """
    Returns _bell_badge.html partial with the current unread count.
    Accepts ?since=<unix_timestamp> — if new notifications exist after that time,
    also injects _toast.html via HTMX OOB into #toast-container.
    Called by HTMX polling every 30s from the header bell badge.
    """
    count = Notification.objects.filter(
        recipient=request.user, is_read=False
    ).count()

    toast = None
    since_param = request.GET.get('since')
    if since_param:
        try:
            since_dt = datetime.fromtimestamp(int(since_param), tz=dt_timezone.utc)
            toast = (
                Notification.objects
                .filter(recipient=request.user, created_at__gt=since_dt)
                .order_by('-created_at')
                .first()
            )
        except (ValueError, OSError, OverflowError):
            pass  # malformed timestamp — silently ignore

    return render(request, 'notifications/_bell_badge.html', {
        'unread_count': count,
        'toast': toast,
    })


@login_required
@require_POST
def mark_read(request, pk):
    """Mark a single notification as read. Only the recipient can mark their own."""
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notif.is_read = True
    notif.save(update_fields=['is_read'])
    if request.htmx:
        return render(request, 'notifications/_notification_item.html', {'notification': notif})
    return redirect('notifications:list')


@login_required
def mark_all_read(request):
    """Mark all of the current user's notifications as read."""
    if request.method == 'POST':
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return redirect('notifications:list')


# ── ALLOWED ROLES FOR COMPOSING MESSAGES ───────────────────────────────────

_COMPOSE_ALLOWED_ROLES = [
    User.Roles.BROKER_ADMIN,
    User.Roles.BROKER_STAFF,
    User.Roles.SUPER_ADMIN,
]


# ── Page Views ──────────────────────────────────────────────────────────────

class NotificationListView(LoginRequiredMixin, View):
    def get(self, request):
        filter_type = request.GET.get('filter', 'all')
        qs = Notification.objects.filter(recipient=request.user)
        if filter_type == 'unread':
            qs = qs.filter(is_read=False)
        return render(request, 'notifications/list.html', {
            'notifications': qs[:50],
            'active_filter': filter_type,
        })


class MessageInboxView(LoginRequiredMixin, View):
    def get(self, request):
        inbox = (
            Message.objects
            .filter(parent=None)
            .filter(
                db_models.Q(sender=request.user) | db_models.Q(recipient=request.user)
            )
            .select_related('sender', 'recipient')
            .order_by('-created_at')
        )
        return render(request, 'notifications/messages_inbox.html', {'inbox': inbox})


class MessageThreadView(LoginRequiredMixin, View):
    def get(self, request, pk):
        # Only root messages are valid thread entry points
        root = get_object_or_404(Message, pk=pk, parent=None)
        if request.user not in (root.sender, root.recipient):
            raise PermissionDenied

        # Mark all messages in this thread as read for the current user
        Message.objects.filter(
            parent=root, recipient=request.user, is_read=False
        ).update(is_read=True)
        if root.recipient == request.user and not root.is_read:
            root.is_read = True
            root.save(update_fields=['is_read'])

        replies = root.replies.select_related('sender', 'recipient').order_by('created_at')
        return render(request, 'notifications/message_thread.html', {
            'root': root,
            'replies': replies,
        })


class ComposeMessageView(LoginRequiredMixin, View):
    def _check_permission(self, request):
        if request.user.role not in _COMPOSE_ALLOWED_ROLES:
            raise PermissionDenied

    def get(self, request):
        self._check_permission(request)
        recipients = (
            User.objects
            .filter(is_active=True)
            .exclude(role__in=[User.Roles.SUPER_ADMIN])
            .order_by('first_name', 'last_name')
        )
        return render(request, 'notifications/messages_inbox.html', {
            'compose_mode': True,
            'recipients': recipients,
        })

    def post(self, request):
        self._check_permission(request)
        recipient_id = request.POST.get('recipient')
        subject = request.POST.get('subject', '').strip()
        body = request.POST.get('body', '').strip()
        attachment = request.FILES.get('attachment')

        if not all([recipient_id, subject, body]):
            recipients = (
                User.objects.filter(is_active=True)
                .exclude(role__in=[User.Roles.SUPER_ADMIN])
                .order_by('first_name', 'last_name')
            )
            return render(request, 'notifications/messages_inbox.html', {
                'compose_mode': True,
                'recipients': recipients,
                'error': 'جميع الحقول مطلوبة.',
            }, status=400)

        # Validate UUID format before hitting the DB (avoids unhandled ValueError)
        try:
            _uuid.UUID(str(recipient_id))
        except ValueError:
            return HttpResponseBadRequest()

        recipient = get_object_or_404(User, pk=recipient_id, is_active=True)
        # Server-side: enforce the SUPER_ADMIN exclusion shown in the UI
        if recipient.role == User.Roles.SUPER_ADMIN:
            raise PermissionDenied

        msg = Message.objects.create(
            sender=request.user,
            recipient=recipient,
            subject=subject,
            body=body,
            attachment=attachment,
        )
        NotificationService.notify_new_message(msg)
        return redirect('notifications:thread', pk=msg.pk)


class ReplyMessageView(LoginRequiredMixin, View):
    def post(self, request, pk):
        root = get_object_or_404(Message, pk=pk)
        # Participant check first — prevents leaking thread structure to outsiders
        if request.user not in (root.sender, root.recipient):
            raise PermissionDenied
        # pk MUST point to a root message — reject replies-to-replies
        if root.parent is not None:
            raise SuspiciousOperation(
                'يجب أن يكون الـ pk لرسالة جذرية (parent=None) فقط.'
            )

        body = request.POST.get('body', '').strip()
        if not body:
            raise SuspiciousOperation('نص الرد مطلوب.')

        # Determine recipient: the other party in the thread
        other_party = root.recipient if request.user == root.sender else root.sender

        reply = Message.objects.create(
            sender=request.user,
            recipient=other_party,
            subject=f'رد: {root.subject}',
            body=body,
            parent=root,
        )
        NotificationService.notify_new_message(reply)
        return redirect('notifications:thread', pk=root.pk)
