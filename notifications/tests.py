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


from django.urls import reverse as url_reverse


class UnreadCountViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='viewuser', password='pass123', role=User.Roles.MEMBER
        )
        self.client.force_login(self.user)

    def test_unread_count_returns_200(self):
        response = self.client.get(url_reverse('notifications:unread-count'))
        self.assertEqual(response.status_code, 200)

    def test_unread_count_requires_login(self):
        self.client.logout()
        response = self.client.get(url_reverse('notifications:unread-count'))
        self.assertEqual(response.status_code, 302)  # redirect to login

    def test_unread_count_shows_correct_count(self):
        Notification.objects.create(
            recipient=self.user, notification_type=Notification.Type.STATUS_CHANGE,
            title='غير مقروء 1',
        )
        Notification.objects.create(
            recipient=self.user, notification_type=Notification.Type.STATUS_CHANGE,
            title='مقروء', is_read=True,
        )
        response = self.client.get(url_reverse('notifications:unread-count'))
        self.assertContains(response, '1')


class MarkReadViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='markuser', password='pass123', role=User.Roles.MEMBER
        )
        self.other = User.objects.create_user(
            username='otheruser', password='pass123', role=User.Roles.MEMBER
        )
        self.client.force_login(self.user)

    def test_mark_read_marks_own_notification(self):
        notif = Notification.objects.create(
            recipient=self.user, notification_type=Notification.Type.STATUS_CHANGE,
            title='اختبار',
        )
        response = self.client.post(
            url_reverse('notifications:mark-read', kwargs={'pk': notif.pk})
        )
        self.assertIn(response.status_code, [200, 302])
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

    def test_mark_read_cannot_mark_others_notification(self):
        other_notif = Notification.objects.create(
            recipient=self.other, notification_type=Notification.Type.STATUS_CHANGE,
            title='لغير المستخدم',
        )
        response = self.client.post(
            url_reverse('notifications:mark-read', kwargs={'pk': other_notif.pk})
        )
        self.assertEqual(response.status_code, 404)
        other_notif.refresh_from_db()
        self.assertFalse(other_notif.is_read)

    def test_mark_all_read(self):
        for i in range(3):
            Notification.objects.create(
                recipient=self.user, notification_type=Notification.Type.STATUS_CHANGE,
                title=f'إشعار {i}',
            )
        response = self.client.post(url_reverse('notifications:mark-all-read'))
        self.assertIn(response.status_code, [200, 302])
        self.assertEqual(
            Notification.objects.filter(recipient=self.user, is_read=False).count(), 0
        )


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


from clients.models import Client


class HRScopingIntegrationTest(TestCase):
    """
    Verifies that HR users from one company do NOT receive notifications
    about service requests from another company's members.
    """

    def setUp(self):
        # Create two separate companies
        self.company_a = Client.objects.create(
            name_ar='شركة الفا', name_en='Alpha Co', commercial_record='CR-TEST-001',
        )
        self.company_b = Client.objects.create(
            name_ar='شركة بيتا', name_en='Beta Co', commercial_record='CR-TEST-002',
        )

        # HR users linked to their respective companies
        self.hr_a = User.objects.create_user(
            username='hr_company_a', password='pass', role=User.Roles.HR_ADMIN,
            related_client=self.company_a, is_active=True,
        )
        self.hr_b = User.objects.create_user(
            username='hr_company_b', password='pass', role=User.Roles.HR_ADMIN,
            related_client=self.company_b, is_active=True,
        )

        # Member user for Company A (sr.member is mocked; .client set directly)
        self.member_user = User.objects.create_user(
            username='member_a', password='pass', role=User.Roles.MEMBER, is_active=True,
        )

    def _make_sr(self):
        """Build a minimal ServiceRequest-like mock for Company A's member."""
        sr = MagicMock()
        sr.pk = uuid.uuid4()
        sr.reference = 'REQ-2026-SCOPING'
        sr.member.client = self.company_a
        sr.member.user = self.member_user
        return sr

    @patch('notifications.services.reverse', return_value='/service-requests/test/')
    def test_hr_from_other_company_does_not_receive_notification(self, mock_reverse):
        sr = self._make_sr()
        NotificationService.notify_service_request_status_change(sr, 'DRAFT', 'SUBMITTED')

        # Company A's HR should receive it
        self.assertEqual(
            Notification.objects.filter(recipient=self.hr_a).count(), 1,
            'HR from Company A should receive notification'
        )
        # Company B's HR must NOT receive it
        self.assertEqual(
            Notification.objects.filter(recipient=self.hr_b).count(), 0,
            'HR from Company B must NOT receive Company A notification'
        )


class SignalIntegrationTest(TestCase):
    """
    Tests that post_save signals correctly call NotificationService.
    Uses @patch to avoid full fixture setup for ServiceRequest / Claim.
    """

    @patch('notifications.signals.ServiceRequest')
    @patch('notifications.signals.NotificationService.notify_service_request_status_change')
    def test_signal_calls_service_on_status_change(self, mock_notify, MockSR):
        mock_instance = MagicMock()
        mock_instance.pk = uuid.uuid4()
        mock_instance.status = 'SUBMITTED'
        mock_instance._original_status = 'DRAFT'

        reloaded = MagicMock()
        MockSR.objects.select_related.return_value.get.return_value = reloaded

        from notifications.signals import sr_notify_on_status_change
        sr_notify_on_status_change(sender=MockSR, instance=mock_instance, created=False)

        mock_notify.assert_called_once_with(reloaded, 'DRAFT', 'SUBMITTED')

    @patch('notifications.signals.NotificationService.notify_service_request_status_change')
    def test_signal_does_not_fire_on_create(self, mock_notify):
        from service_requests.models import ServiceRequest
        from notifications.signals import sr_notify_on_status_change
        mock_instance = MagicMock(spec=ServiceRequest)
        mock_instance.status = 'DRAFT'
        sr_notify_on_status_change(sender=ServiceRequest, instance=mock_instance, created=True)
        mock_notify.assert_not_called()

    @patch('notifications.signals.NotificationService.notify_service_request_status_change')
    def test_signal_does_not_fire_when_status_unchanged(self, mock_notify):
        from service_requests.models import ServiceRequest
        from notifications.signals import sr_notify_on_status_change
        mock_instance = MagicMock(spec=ServiceRequest)
        mock_instance.status = 'SUBMITTED'
        mock_instance._original_status = 'SUBMITTED'
        sr_notify_on_status_change(sender=ServiceRequest, instance=mock_instance, created=False)
        mock_notify.assert_not_called()

    @patch('notifications.signals.Claim')
    @patch('notifications.signals.NotificationService.notify_claim_status_change')
    def test_claim_signal_calls_service_on_status_change(self, mock_notify, MockClaim):
        mock_instance = MagicMock()
        mock_instance.pk = uuid.uuid4()
        mock_instance.status = 'SUBMITTED_TO_HR'
        mock_instance._original_status = 'DRAFT'

        reloaded = MagicMock()
        MockClaim.objects.select_related.return_value.get.return_value = reloaded

        from notifications.signals import claim_notify_on_status_change
        claim_notify_on_status_change(sender=MockClaim, instance=mock_instance, created=False)

        mock_notify.assert_called_once_with(reloaded, 'DRAFT', 'SUBMITTED_TO_HR')

    def test_pre_save_sets_none_for_new_records(self):
        """New records (pk set but not yet in DB) should get _original_status = None."""
        from service_requests.models import ServiceRequest
        from notifications.signals import sr_capture_old_status

        # Create a mock instance that simulates a new (unsaved) object
        mock_instance = MagicMock(spec=ServiceRequest)
        mock_instance.pk = uuid.uuid4()
        mock_instance._state = MagicMock()
        mock_instance._state.adding = True  # New object not yet in DB

        sr_capture_old_status(sender=ServiceRequest, instance=mock_instance, using='default')

        self.assertIsNone(mock_instance._original_status)
