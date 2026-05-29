# notifications/services.py
from django.urls import reverse
from accounts.models import User
from .models import Notification


class NotificationService:
    """
    Routing logic for all notification dispatch.
    Keeps signal handlers thin — signals detect the change, this class decides who gets notified.
    """

    # --- Service Request routing map ---
    # Keys: new status values that trigger a notification
    # 'to': 'member' | 'hr' | 'both'
    SR_ROUTING = {
        'SUBMITTED': {
            'to': 'hr',
            'title': 'طلب خدمة جديد يحتاج مراجعتك — {reference}',
        },
        'IN_REVIEW': {
            'to': 'member',
            'title': 'طلبك {reference} قيد المراجعة من قِبل الوسيط',
        },
        'RETURNED': {
            'to': 'member',
            'title': 'طلبك {reference} أُعيد — يرجى مراجعة الملاحظات',
        },
        'RESOLVED': {
            'to': 'member',
            'title': 'طلبك {reference} تم حله بنجاح ✅',
        },
        'REJECTED': {
            'to': 'member',
            'title': 'طلبك {reference} تم رفضه',
        },
    }
    # Statuses with no notification: DRAFT, HR_REVIEW, TRANSFERRED_TO_MEDICATIONS

    # --- Claim routing map ---
    CLAIM_ROUTING = {
        'SUBMITTED_TO_HR': {
            'to': 'hr',
            'title': 'مطالبة جديدة تحتاج مراجعتك — {reference}',
        },
        'RETURNED_BY_HR': {
            'to': 'member',
            'title': 'مطالبتك {reference} أُعيدت — ناقص مستندات',
        },
        'SUBMITTED_TO_BROKER': {
            'to': 'member',
            'title': 'مطالبتك {reference} أُحيلت للوسيط للمراجعة',
        },
        'RETURNED_BY_BROKER': {
            'to': 'both',
            'title': 'مطالبة {reference} أُعيدت من الوسيط — يحتاج إجراء',
        },
        'SENT_TO_INSURANCE': {
            'to': 'member',
            'title': 'مطالبتك {reference} أُرسلت لشركة التأمين',
        },
        'APPROVED_BY_INSURANCE': {
            'to': 'both',
            'title': 'مطالبتك {reference} وافقت عليها شركة التأمين ✅',
        },
        'REJECTED_BY_INSURANCE': {
            'to': 'both',
            'title': 'مطالبتك {reference} رُفضت من شركة التأمين',
        },
        'PAID': {
            'to': 'member',
            'title': 'تم صرف مستحقات مطالبتك {reference} 💰',
        },
    }
    # Statuses with no notification: DRAFT, BROKER_PROCESSING, INSURANCE_QUERY

    @classmethod
    def _collect_recipients(cls, rule, instance):
        """
        Return a list of User objects to notify based on the routing rule.
        instance must already be loaded with select_related('member__client', 'member__user').
        """
        recipients = []
        target = rule['to']

        if target in ('member', 'both'):
            member_user = instance.member.user
            if member_user and member_user.is_active:
                recipients.append(member_user)

        if target in ('hr', 'both'):
            hr_users = User.objects.filter(
                role__in=[User.Roles.HR_ADMIN, User.Roles.HR_STAFF],
                related_client=instance.member.client,
                is_active=True,
            )
            recipients.extend(list(hr_users))

        return recipients

    @classmethod
    def notify_service_request_status_change(cls, instance, old_status, new_status):
        """
        Called by the post_save signal for ServiceRequest.
        instance must be loaded with select_related('member__client', 'member__user').
        """
        rule = cls.SR_ROUTING.get(new_status)
        if not rule:
            return

        title = rule['title'].format(reference=instance.reference)
        url = reverse('service_requests:request_detail', kwargs={'pk': instance.pk})
        recipients = cls._collect_recipients(rule, instance)

        if not recipients:
            return

        Notification.objects.bulk_create([
            Notification(
                recipient=user,
                notification_type=Notification.Type.STATUS_CHANGE,
                title=title,
                url=url,
            )
            for user in recipients
        ])

    @classmethod
    def notify_claim_status_change(cls, instance, old_status, new_status):
        """
        Called by the post_save signal for Claim.
        instance must be loaded with select_related('member__client', 'member__user').
        """
        rule = cls.CLAIM_ROUTING.get(new_status)
        if not rule:
            return

        title = rule['title'].format(reference=instance.claim_reference)
        url = reverse('claims:claim_detail', kwargs={'pk': instance.pk})
        recipients = cls._collect_recipients(rule, instance)

        if not recipients:
            return

        Notification.objects.bulk_create([
            Notification(
                recipient=user,
                notification_type=Notification.Type.STATUS_CHANGE,
                title=title,
                url=url,
            )
            for user in recipients
        ])

    @classmethod
    def notify_new_message(cls, message):
        """
        Called after creating a Message (root or reply).
        Creates a Notification for the recipient.
        """
        is_reply = message.parent is not None
        notif_type = Notification.Type.REPLY if is_reply else Notification.Type.MESSAGE

        sender_name = message.sender.get_full_name() or message.sender.username
        if is_reply:
            title = f'رد جديد من {sender_name}'
        else:
            title = f'رسالة جديدة من {sender_name}: {message.subject}'

        # URL points to thread root (always accessible for participants)
        root_pk = message.parent.pk if is_reply else message.pk
        url = reverse('notifications:thread', kwargs={'pk': root_pk})

        Notification.objects.create(
            recipient=message.recipient,
            notification_type=notif_type,
            title=title,
            url=url,
        )
