# notifications/views.py
from datetime import datetime, timezone as dt_timezone

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Notification


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
def mark_read(request, pk):
    """Mark a single notification as read. Only the recipient can mark their own."""
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notif.is_read = True
    notif.save(update_fields=['is_read'])
    if request.htmx:
        return render(request, 'notifications/_notification_item.html', {'notification': notif})
    return redirect('/')


@login_required
def mark_all_read(request):
    """Mark all of the current user's notifications as read."""
    if request.method == 'POST':
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return redirect('/')
