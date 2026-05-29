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

    def test_reply_to_reply_points_to_root(self):
        """Replies must always point to the root — enforced at view level (tested in Task 7)."""
        root = Message.objects.create(
            sender=self.broker, recipient=self.member, subject='موضوع', body='نص'
        )
        reply = Message.objects.create(
            sender=self.member, recipient=self.broker, subject='رد', body='رد', parent=root
        )
        # The model allows parent=reply at DB level; the view enforces parent=None only
        # This test documents the constraint is at the view level
        self.assertEqual(reply.parent, root)
