# notifications/tests.py
import uuid
from django.test import TestCase
from accounts.models import User
from .models import Notification, Message


class NotificationModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testmember', password='testpass123', role=User.Roles.MEMBER
        )

    def test_notification_created_with_defaults(self):
        notif = Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.Type.STATUS_CHANGE,
            title='طلبك REQ-2026-00001 قيد المراجعة',
        )
        self.assertFalse(notif.is_read)
        self.assertIsNotNone(notif.id)
        self.assertIsNone(notif.content_type)
        self.assertIsNone(notif.object_id)

    def test_notification_ordering_latest_first(self):
        Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.Type.STATUS_CHANGE,
            title='الأول',
        )
        Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.Type.STATUS_CHANGE,
            title='الثاني',
        )
        titles = list(
            Notification.objects.filter(recipient=self.user).values_list('title', flat=True)
        )
        self.assertEqual(titles[0], 'الثاني')

    def test_unread_count_query(self):
        Notification.objects.create(
            recipient=self.user, notification_type=Notification.Type.STATUS_CHANGE,
            title='مقروء', is_read=True,
        )
        Notification.objects.create(
            recipient=self.user, notification_type=Notification.Type.STATUS_CHANGE,
            title='غير مقروء',
        )
        count = Notification.objects.filter(recipient=self.user, is_read=False).count()
        self.assertEqual(count, 1)


class MessageModelTest(TestCase):
    def setUp(self):
        self.broker = User.objects.create_user(
            username='broker1', password='pass123', role=User.Roles.BROKER_ADMIN
        )
        self.member = User.objects.create_user(
            username='member1', password='pass123', role=User.Roles.MEMBER
        )

    def test_root_message_has_no_parent(self):
        msg = Message.objects.create(
            sender=self.broker,
            recipient=self.member,
            subject='موضوع الرسالة',
            body='نص الرسالة',
        )
        self.assertIsNone(msg.parent)
        self.assertFalse(msg.is_read)
        self.assertIsNotNone(msg.id)

    def test_reply_points_to_root_only(self):
        root = Message.objects.create(
            sender=self.broker, recipient=self.member,
            subject='موضوع', body='نص',
        )
        reply = Message.objects.create(
            sender=self.member, recipient=self.broker,
            subject='رد', body='نص الرد', parent=root,
        )
        self.assertEqual(reply.parent, root)
        self.assertEqual(root.replies.count(), 1)

    def test_reply_to_reply_is_permitted_at_model_level(self):
        """Model allows deep nesting at DB level; the view must enforce flat threads."""
        root = Message.objects.create(
            sender=self.broker, recipient=self.member, subject='موضوع', body='نص'
        )
        reply = Message.objects.create(
            sender=self.member, recipient=self.broker, subject='رد', body='رد', parent=root
        )
        nested = Message.objects.create(
            sender=self.broker, recipient=self.member, subject='رد متداخل', body='نص', parent=reply
        )
        # DB allows it — view must reject it (tested in Task 7 MessageViewTest)
        self.assertEqual(nested.parent, reply)
        self.assertIsNotNone(nested.pk)


from unittest.mock import patch, MagicMock
from .services import NotificationService


class NotificationServiceTest(TestCase):
    def setUp(self):
        self.hr_user = User.objects.create_user(
            username='hr_staff', password='pass123', role=User.Roles.HR_ADMIN
        )
        self.member_user = User.objects.create_user(
            username='member2', password='pass123', role=User.Roles.MEMBER
        )

    def _make_sr_instance(self, reference='REQ-2026-00001'):
        """Build a mock ServiceRequest-like object."""
        instance = MagicMock()
        instance.pk = uuid.uuid4()
        instance.reference = reference
        instance.member.user = self.member_user
        instance.member.client = MagicMock()
        return instance

    @patch('notifications.services.User')
    def test_no_notification_for_unmapped_status(self, MockUser):
        instance = self._make_sr_instance()
        NotificationService.notify_service_request_status_change(instance, 'DRAFT', 'HR_REVIEW')
        self.assertEqual(Notification.objects.count(), 0)

    @patch('notifications.services.User')
    @patch('notifications.services.reverse', return_value='/service-requests/test/')
    def test_submitted_notifies_hr_only(self, mock_reverse, MockUser):
        MockUser.objects.filter.return_value = User.objects.filter(pk=self.hr_user.pk)
        MockUser.Roles = User.Roles
        instance = self._make_sr_instance()

        NotificationService.notify_service_request_status_change(instance, 'DRAFT', 'SUBMITTED')

        notifs = Notification.objects.filter(recipient=self.hr_user)
        self.assertEqual(notifs.count(), 1)
        self.assertIn('REQ-2026-00001', notifs.first().title)
        self.assertEqual(notifs.first().notification_type, Notification.Type.STATUS_CHANGE)
        # Member must NOT be notified for SUBMITTED
        self.assertEqual(Notification.objects.filter(recipient=self.member_user).count(), 0)

    @patch('notifications.services.User')
    @patch('notifications.services.reverse', return_value='/service-requests/test/')
    def test_in_review_notifies_member_only(self, mock_reverse, MockUser):
        MockUser.objects.filter.return_value = User.objects.none()
        MockUser.Roles = User.Roles
        instance = self._make_sr_instance()

        NotificationService.notify_service_request_status_change(instance, 'SUBMITTED', 'IN_REVIEW')

        self.assertEqual(Notification.objects.filter(recipient=self.member_user).count(), 1)
        self.assertEqual(Notification.objects.filter(recipient=self.hr_user).count(), 0)

    @patch('notifications.services.User')
    @patch('notifications.services.reverse', return_value='/claims/test/')
    def test_claim_returned_by_broker_notifies_both(self, mock_reverse, MockUser):
        MockUser.objects.filter.return_value = User.objects.filter(pk=self.hr_user.pk)
        MockUser.Roles = User.Roles
        instance = MagicMock()
        instance.pk = uuid.uuid4()
        instance.claim_reference = 'CLM-2026-00001'
        instance.member.user = self.member_user
        instance.member.client = MagicMock()

        NotificationService.notify_claim_status_change(instance, 'SUBMITTED_TO_BROKER', 'RETURNED_BY_BROKER')

        self.assertEqual(Notification.objects.filter(recipient=self.member_user).count(), 1)
        self.assertEqual(Notification.objects.filter(recipient=self.hr_user).count(), 1)

    @patch('notifications.services.reverse', return_value='/notifications/messages/test/')
    def test_notify_new_message_creates_notification(self, mock_reverse):
        broker = User.objects.create_user(username='brkr2', password='p', role=User.Roles.BROKER_ADMIN)
        member = User.objects.create_user(username='mbr2', password='p', role=User.Roles.MEMBER)
        msg = Message.objects.create(sender=broker, recipient=member, subject='اختبار', body='نص')

        NotificationService.notify_new_message(msg)

        notif = Notification.objects.get(recipient=member)
        self.assertEqual(notif.notification_type, Notification.Type.MESSAGE)

    @patch('notifications.services.reverse', return_value='/notifications/messages/test/')
    def test_notify_reply_creates_reply_type_notification(self, mock_reverse):
        broker = User.objects.create_user(username='brkr3', password='p', role=User.Roles.BROKER_ADMIN)
        member = User.objects.create_user(username='mbr3', password='p', role=User.Roles.MEMBER)
        root = Message.objects.create(sender=broker, recipient=member, subject='اختبار', body='نص')
        reply = Message.objects.create(
            sender=member, recipient=broker, subject='رد', body='رد', parent=root
        )

        NotificationService.notify_new_message(reply)

        notif = Notification.objects.get(recipient=broker)
        self.assertEqual(notif.notification_type, Notification.Type.REPLY)
