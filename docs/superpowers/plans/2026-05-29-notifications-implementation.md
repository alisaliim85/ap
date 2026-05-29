# Notifications System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full in-app notification system for AP PLUS — automatic status-change alerts for `service_requests` and `claims`, plus a bidirectional internal messaging inbox with thread support.

**Architecture:** Standalone `notifications/` Django app. Django Signals (synchronous, same DB transaction) dispatch `Notification` records on status changes. HTMX polls `/notifications/unread-count/` every 30 seconds for the bell badge. Alpine.js handles adaptive backoff and toast display. No Celery, no WebSocket, no changes to `service_requests/` or `claims/` files.

**Tech Stack:** Django 4.2, HTMX 1.9.6, Alpine.js 3.x, Tailwind CSS 3, Phosphor Icons, SQLite

---

## Reference: URL Names (verified from codebase)

| App | View | URL name |
|---|---|---|
| service_requests | detail page | `service_requests:request_detail` |
| claims | detail page | `claims:claim_detail` |
| notifications | bell badge partial | `notifications:unread-count` |
| notifications | mark one read | `notifications:mark-read` |
| notifications | mark all read | `notifications:mark-all-read` |
| notifications | list page | `notifications:list` |
| notifications | inbox | `notifications:inbox` |
| notifications | thread | `notifications:thread` |
| notifications | compose | `notifications:compose` |
| notifications | reply | `notifications:reply` |

## Reference: User Roles (from `accounts.models.User.Roles`)

```
SUPER_ADMIN, BROKER_ADMIN, BROKER_STAFF, HR_ADMIN, HR_STAFF,
PHARMACIST, CHRONIC_ADMIN, CHRONIC_STAFF, VIEWER, INSURANCE, MEMBER
```

## Reference: Member→User relationship

`Member.user` is a nullable `OneToOneField` to `accounts.User` with `related_name='member_profile'`.
`member.user` returns `None` if the member has no user account — safe to access directly.

---

## File Structure

**New files:**

```
notifications/
├── __init__.py                 ← empty
├── apps.py                     ← AppConfig; calls import notifications.signals in ready()
├── models.py                   ← Notification + Message models
├── signals.py                  ← pre_save + post_save for ServiceRequest and Claim
├── services.py                 ← NotificationService — routing maps + bulk_create logic
├── views.py                    ← 8 views
├── urls.py                     ← app_name='notifications', 8 URL patterns
├── admin.py                    ← NotificationAdmin + MessageAdmin
├── tests.py                    ← all tests (models, service, signals, views)
└── migrations/
    └── __init__.py             ← empty

templates/notifications/
├── _bell_badge.html            ← HTMX self-polling partial (outerHTML swap)
├── _toast.html                 ← HTMX OOB partial injected into #toast-container
├── _notification_item.html     ← single notification row (used in list.html loop)
├── list.html                   ← full notification list page
├── messages_inbox.html         ← message threads list page
└── message_thread.html         ← thread detail + reply form
```

**Modified files:**

```
config/settings.py              ← add 'notifications' to INSTALLED_APPS
config/urls.py                  ← add path('notifications/', include('notifications.urls'))
templates/includes/header.html  ← replace static bell button with HTMX-powered badge
templates/base.html             ← add JS helper for ?since= parameter on polling requests
```

---

## Task 1: App Scaffolding

**Files:**
- Create: `notifications/__init__.py`
- Create: `notifications/apps.py`
- Create: `notifications/urls.py` (skeleton only)
- Create: `notifications/migrations/__init__.py`
- Modify: `config/settings.py`
- Modify: `config/urls.py`

- [ ] **Step 1: Create `notifications/__init__.py`**

```python
# notifications/__init__.py
# (empty file)
```

- [ ] **Step 2: Create `notifications/apps.py`**

```python
# notifications/apps.py
from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'
    verbose_name = 'الإشعارات'

    def ready(self):
        import notifications.signals  # noqa: F401 — registers signal handlers
```

- [ ] **Step 3: Create `notifications/urls.py` (skeleton)**

```python
# notifications/urls.py
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = []
```

- [ ] **Step 4: Create `notifications/migrations/__init__.py`**

```python
# notifications/migrations/__init__.py
# (empty file)
```

- [ ] **Step 5: Add `'notifications'` to `INSTALLED_APPS` in `config/settings.py`**

Find the block ending with `'medications'` and add one line after it:

```python
    'medications',
    'notifications',
```

- [ ] **Step 6: Add URL include in `config/urls.py`**

Find the line `path('medications/', include('medications.urls')),` and add after it:

```python
    path('medications/', include('medications.urls')),
    path('notifications/', include('notifications.urls')),
```

- [ ] **Step 7: Run system check**

```
py manage.py check
```

Expected output: `System check identified no issues (0 silenced).`

- [ ] **Step 8: Commit**

```
git add notifications/ config/settings.py config/urls.py
git commit -m "feat(notifications): scaffold app skeleton"
```

---

## Task 2: Models + Migrations

**Files:**
- Create: `notifications/models.py`
- Create: `notifications/tests.py`

- [ ] **Step 1: Write failing tests in `notifications/tests.py`**

```python
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
```

- [ ] **Step 2: Run tests — verify they FAIL (models not created yet)**

```
py manage.py test notifications.tests.NotificationModelTest notifications.tests.MessageModelTest -v 2
```

Expected: `ImportError: cannot import name 'Notification' from 'notifications.models'`

- [ ] **Step 3: Create `notifications/models.py`**

```python
# notifications/models.py
import uuid
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings


class Notification(models.Model):
    class Type(models.TextChoices):
        STATUS_CHANGE = 'STATUS_CHANGE', 'تغيير حالة'
        MESSAGE = 'MESSAGE', 'رسالة جديدة'
        REPLY = 'REPLY', 'رد جديد'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    notification_type = models.CharField(max_length=20, choices=Type.choices)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    url = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    # GenericFK — links to any model (ServiceRequest, Claim, ...)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    object_id = models.UUIDField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', 'created_at']),
        ]

    def __str__(self):
        return f"{self.recipient} — {self.title[:50]}"


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages',
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_messages',
    )
    subject = models.CharField(max_length=300)
    body = models.TextField()
    # Thread: root messages have parent=None; replies point directly to root
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='replies',
    )
    # Attachments only on root messages (enforced at view level)
    attachment = models.FileField(
        upload_to='notifications/attachments/%Y/%m/',
        null=True, blank=True,
    )
    is_read = models.BooleanField(default=False, db_index=True)
    # Optional link to any model (ServiceRequest, Claim)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    object_id = models.UUIDField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
        ]

    def __str__(self):
        return f"{self.sender} → {self.recipient}: {self.subject[:50]}"
```

- [ ] **Step 4: Create and apply migration**

```
py manage.py makemigrations notifications
py manage.py migrate
```

Expected: migration `notifications/migrations/0001_initial.py` created; `migrate` applies cleanly.

- [ ] **Step 5: Run tests — verify they PASS**

```
py manage.py test notifications.tests.NotificationModelTest notifications.tests.MessageModelTest -v 2
```

Expected: `OK` — 5 tests pass.

- [ ] **Step 6: Commit**

```
git add notifications/ config/settings.py config/urls.py
git commit -m "feat(notifications): add Notification and Message models"
```

---

## Task 3: Admin

**Files:**
- Create: `notifications/admin.py`

- [ ] **Step 1: Create `notifications/admin.py`**

```python
# notifications/admin.py
from django.contrib import admin
from .models import Notification, Message


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    # raw_id_fields works on FK fields (recipient, content_type) — NOT on UUIDField (object_id)
    raw_id_fields = ('recipient', 'content_type')
    readonly_fields = ('content_object',)   # GenericFK — display only, no dropdown
    list_per_page = 25
    list_select_related = True
    list_display = ('recipient', 'notification_type', 'title', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('recipient__username', 'recipient__first_name', 'title')
    date_hierarchy = 'created_at'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    raw_id_fields = ('sender', 'recipient', 'parent', 'content_type')
    readonly_fields = ('content_object',)
    list_per_page = 25
    list_select_related = True
    list_display = ('sender', 'recipient', 'subject', 'is_read', 'created_at')
    search_fields = ('sender__username', 'recipient__username', 'subject')
    date_hierarchy = 'created_at'
```

- [ ] **Step 2: Verify admin registers cleanly**

```
py manage.py check
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 3: Commit**

```
git add notifications/admin.py
git commit -m "feat(notifications): add admin for Notification and Message"
```

---

## Task 4: NotificationService

**Files:**
- Create: `notifications/services.py`
- Extend: `notifications/tests.py`

- [ ] **Step 1: Add service tests to `notifications/tests.py`**

Append this class to the existing `tests.py`:

```python
from unittest.mock import patch, MagicMock, PropertyMock
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
```

- [ ] **Step 2: Run tests — verify they FAIL**

```
py manage.py test notifications.tests.NotificationServiceTest -v 2
```

Expected: `ImportError: cannot import name 'NotificationService' from 'notifications.services'`

- [ ] **Step 3: Create `notifications/services.py`**

```python
# notifications/services.py
from django.urls import reverse
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
        from accounts.models import User

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
```

- [ ] **Step 4: Run tests — verify they PASS**

```
py manage.py test notifications.tests.NotificationServiceTest -v 2
```

Expected: `OK` — 6 tests pass.

- [ ] **Step 5: Commit**

```
git add notifications/services.py notifications/tests.py
git commit -m "feat(notifications): add NotificationService with routing logic"
```

---

## Task 5: Signals

**Files:**
- Create: `notifications/signals.py`
- Modify: `notifications/apps.py` (already imports signals in `ready()` — no change needed)
- Extend: `notifications/tests.py`

- [ ] **Step 1: Add signal integration tests to `notifications/tests.py`**

Append this class to the existing `tests.py`:

```python
from unittest.mock import patch


class SignalIntegrationTest(TestCase):
    """
    Tests that post_save signals correctly call NotificationService.
    Uses @patch to avoid full fixture setup for ServiceRequest / Claim.
    """

    @patch('notifications.signals.NotificationService.notify_service_request_status_change')
    def test_signal_calls_service_on_status_change(self, mock_notify):
        from service_requests.models import ServiceRequest
        # Simulate a save where status changes from DRAFT to SUBMITTED
        # We patch the service method to avoid needing a full DB fixture
        mock_instance = MagicMock(spec=ServiceRequest)
        mock_instance.pk = uuid.uuid4()
        mock_instance.status = 'SUBMITTED'

        # Import and call the signal handler directly
        from notifications.signals import sr_notify_on_status_change
        mock_instance.__original_status = 'DRAFT'
        sr_notify_on_status_change(sender=ServiceRequest, instance=mock_instance, created=False)

        mock_notify.assert_called_once()
        args = mock_notify.call_args[0]
        self.assertEqual(args[1], 'DRAFT')    # old_status
        self.assertEqual(args[2], 'SUBMITTED')  # new_status

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
        mock_instance.__original_status = 'SUBMITTED'
        sr_notify_on_status_change(sender=ServiceRequest, instance=mock_instance, created=False)
        mock_notify.assert_not_called()

    @patch('notifications.signals.NotificationService.notify_claim_status_change')
    def test_claim_signal_calls_service_on_status_change(self, mock_notify):
        from claims.models import Claim
        from notifications.signals import claim_notify_on_status_change
        mock_instance = MagicMock(spec=Claim)
        mock_instance.pk = uuid.uuid4()
        mock_instance.status = 'SUBMITTED_TO_HR'
        mock_instance.__original_status = 'DRAFT'
        claim_notify_on_status_change(sender=Claim, instance=mock_instance, created=False)
        mock_notify.assert_called_once()
```

- [ ] **Step 2: Run tests — verify they FAIL**

```
py manage.py test notifications.tests.SignalIntegrationTest -v 2
```

Expected: `ImportError: cannot import name 'sr_notify_on_status_change' from 'notifications.signals'`

- [ ] **Step 3: Create `notifications/signals.py`**

```python
# notifications/signals.py
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from service_requests.models import ServiceRequest
from claims.models import Claim
from .services import NotificationService


# ── ServiceRequest Signals ──────────────────────────────────────────────────

@receiver(pre_save, sender=ServiceRequest)
def sr_capture_old_status(sender, instance, **kwargs):
    """
    Store the current DB status on the instance before saving.
    post_save handler uses __original_status to detect actual changes.
    """
    if instance.pk:
        try:
            old = ServiceRequest.objects.get(pk=instance.pk)
            instance.__original_status = old.status
        except ServiceRequest.DoesNotExist:
            instance.__original_status = None
    else:
        instance.__original_status = None


@receiver(post_save, sender=ServiceRequest)
def sr_notify_on_status_change(sender, instance, created, **kwargs):
    """
    Fire notification if status actually changed.
    Reloads instance with select_related to avoid N+1.
    """
    if created:
        return
    old_status = getattr(instance, '__original_status', None)
    new_status = instance.status
    if old_status is None or old_status == new_status:
        return

    # One DB hit instead of three (instance → member → member.client)
    fresh = ServiceRequest.objects.select_related(
        'member__client', 'member__user'
    ).get(pk=instance.pk)

    NotificationService.notify_service_request_status_change(fresh, old_status, new_status)


# ── Claim Signals ───────────────────────────────────────────────────────────

@receiver(pre_save, sender=Claim)
def claim_capture_old_status(sender, instance, **kwargs):
    """
    Same pattern as ServiceRequest — capture status before FSM transition saves.
    """
    if instance.pk:
        try:
            old = Claim.objects.get(pk=instance.pk)
            instance.__original_status = old.status
        except Claim.DoesNotExist:
            instance.__original_status = None
    else:
        instance.__original_status = None


@receiver(post_save, sender=Claim)
def claim_notify_on_status_change(sender, instance, created, **kwargs):
    """
    Fire notification when Claim status transitions via FSM.
    """
    if created:
        return
    old_status = getattr(instance, '__original_status', None)
    new_status = instance.status
    if old_status is None or old_status == new_status:
        return

    fresh = Claim.objects.select_related(
        'member__client', 'member__user'
    ).get(pk=instance.pk)

    NotificationService.notify_claim_status_change(fresh, old_status, new_status)
```

- [ ] **Step 4: Run tests — verify they PASS**

```
py manage.py test notifications.tests.SignalIntegrationTest -v 2
```

Expected: `OK` — 4 tests pass.

- [ ] **Step 5: Run all notifications tests to confirm nothing broke**

```
py manage.py test notifications -v 2
```

Expected: `OK` — all previous tests still pass.

- [ ] **Step 6: Commit**

```
git add notifications/signals.py notifications/tests.py
git commit -m "feat(notifications): add signals for ServiceRequest and Claim status changes"
```

---

## Task 6: HTMX Partial Views (unread_count, mark_read, mark_all_read)

**Files:**
- Create: `notifications/views.py`
- Modify: `notifications/urls.py`
- Extend: `notifications/tests.py`

- [ ] **Step 1: Add view tests to `notifications/tests.py`**

Append this class:

```python
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
```

- [ ] **Step 2: Run tests — verify they FAIL**

```
py manage.py test notifications.tests.UnreadCountViewTest notifications.tests.MarkReadViewTest -v 2
```

Expected: `NoReverseMatch` (URLs not wired yet)

- [ ] **Step 3: Create `notifications/views.py` with the 3 partial views**

```python
# notifications/views.py
from datetime import datetime, timezone as dt_timezone

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.db import models as db_models
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

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
```

- [ ] **Step 4: Wire the 3 partial URLs in `notifications/urls.py`**

```python
# notifications/urls.py
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # HTMX partial: bell badge polling
    path('unread-count/', views.unread_count, name='unread-count'),
    # Mark actions
    path('mark-read/<uuid:pk>/', views.mark_read, name='mark-read'),
    path('mark-all-read/', views.mark_all_read, name='mark-all-read'),
]
```

- [ ] **Step 5: Run tests — verify they PASS**

```
py manage.py test notifications.tests.UnreadCountViewTest notifications.tests.MarkReadViewTest -v 2
```

Expected: `OK` — all 6 tests pass.

- [ ] **Step 6: Commit**

```
git add notifications/views.py notifications/urls.py notifications/tests.py
git commit -m "feat(notifications): add HTMX partial views (unread-count, mark-read)"
```

---

## Task 7: Page Views (list, inbox, thread, compose, reply)

**Files:**
- Extend: `notifications/views.py`
- Extend: `notifications/urls.py`
- Extend: `notifications/tests.py`

- [ ] **Step 1: Add page view tests to `notifications/tests.py`**

Append:

```python
class NotificationListViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='listuser', password='pass123', role=User.Roles.MEMBER
        )
        self.client.force_login(self.user)

    def test_list_requires_login(self):
        self.client.logout()
        response = self.client.get(url_reverse('notifications:list'))
        self.assertEqual(response.status_code, 302)

    def test_list_shows_only_own_notifications(self):
        other = User.objects.create_user(username='listother', password='p', role=User.Roles.MEMBER)
        Notification.objects.create(
            recipient=self.user, notification_type=Notification.Type.STATUS_CHANGE, title='لي'
        )
        Notification.objects.create(
            recipient=other, notification_type=Notification.Type.STATUS_CHANGE, title='لغيري'
        )
        response = self.client.get(url_reverse('notifications:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'لي')
        self.assertNotContains(response, 'لغيري')


class MessageViewTest(TestCase):
    def setUp(self):
        self.broker = User.objects.create_user(
            username='brk_view', password='pass123', role=User.Roles.BROKER_ADMIN
        )
        self.member = User.objects.create_user(
            username='mbr_view', password='pass123', role=User.Roles.MEMBER
        )

    def test_compose_requires_broker_role(self):
        self.client.force_login(self.member)
        response = self.client.get(url_reverse('notifications:compose'))
        self.assertEqual(response.status_code, 403)

    def test_compose_accessible_to_broker(self):
        self.client.force_login(self.broker)
        response = self.client.get(url_reverse('notifications:compose'))
        self.assertEqual(response.status_code, 200)

    def test_inbox_requires_login(self):
        response = self.client.get(url_reverse('notifications:inbox'))
        self.assertEqual(response.status_code, 302)

    def test_thread_view_accessible_to_sender(self):
        self.client.force_login(self.broker)
        root = Message.objects.create(
            sender=self.broker, recipient=self.member, subject='موضوع', body='نص'
        )
        response = self.client.get(url_reverse('notifications:thread', kwargs={'pk': root.pk}))
        self.assertEqual(response.status_code, 200)

    def test_thread_view_accessible_to_recipient(self):
        self.client.force_login(self.member)
        root = Message.objects.create(
            sender=self.broker, recipient=self.member, subject='موضوع', body='نص'
        )
        response = self.client.get(url_reverse('notifications:thread', kwargs={'pk': root.pk}))
        self.assertEqual(response.status_code, 200)

    def test_thread_view_blocked_for_non_participant(self):
        stranger = User.objects.create_user(
            username='stranger', password='p', role=User.Roles.MEMBER
        )
        self.client.force_login(stranger)
        root = Message.objects.create(
            sender=self.broker, recipient=self.member, subject='موضوع', body='نص'
        )
        response = self.client.get(url_reverse('notifications:thread', kwargs={'pk': root.pk}))
        self.assertEqual(response.status_code, 403)

    def test_thread_view_returns_404_for_reply_pk(self):
        """reply/ pk must point to a root message only."""
        self.client.force_login(self.broker)
        root = Message.objects.create(
            sender=self.broker, recipient=self.member, subject='موضوع', body='نص'
        )
        reply = Message.objects.create(
            sender=self.member, recipient=self.broker,
            subject='رد', body='رد', parent=root
        )
        response = self.client.get(url_reverse('notifications:thread', kwargs={'pk': reply.pk}))
        self.assertEqual(response.status_code, 404)

    def test_reply_rejected_for_non_participant(self):
        stranger = User.objects.create_user(
            username='stranger2', password='p', role=User.Roles.MEMBER
        )
        self.client.force_login(stranger)
        root = Message.objects.create(
            sender=self.broker, recipient=self.member, subject='موضوع', body='نص'
        )
        response = self.client.post(
            url_reverse('notifications:reply', kwargs={'pk': root.pk}),
            {'body': 'محاولة رد غير مصرح بها'},
        )
        self.assertEqual(response.status_code, 403)

    def test_reply_rejected_when_pk_is_reply(self):
        """reply/ endpoint must return 400 if pk is not a root message."""
        self.client.force_login(self.member)
        root = Message.objects.create(
            sender=self.broker, recipient=self.member, subject='موضوع', body='نص'
        )
        reply = Message.objects.create(
            sender=self.member, recipient=self.broker, subject='رد', body='رد', parent=root
        )
        response = self.client.post(
            url_reverse('notifications:reply', kwargs={'pk': reply.pk}),
            {'body': 'محاولة'},
        )
        self.assertEqual(response.status_code, 400)
```

- [ ] **Step 2: Run tests — verify they FAIL**

```
py manage.py test notifications.tests.NotificationListViewTest notifications.tests.MessageViewTest -v 2
```

Expected: `NoReverseMatch` (URLs not wired yet)

- [ ] **Step 3: Add page views to `notifications/views.py`**

Append to the existing `views.py` (after `mark_all_read`):

```python
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

        recipient = get_object_or_404(User, pk=recipient_id, is_active=True)
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
        # pk MUST point to a root message — reject replies-to-replies
        root = get_object_or_404(Message, pk=pk)
        if root.parent is not None:
            raise SuspiciousOperation(
                'يجب أن يكون الـ pk لرسالة جذرية (parent=None) فقط.'
            )
        if request.user not in (root.sender, root.recipient):
            raise PermissionDenied

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
```

- [ ] **Step 4: Add all 5 page URLs to `notifications/urls.py`**

Replace the entire `urlpatterns` list:

```python
# notifications/urls.py
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # ── Notification views ──────────────────────────────────────────────────
    path('', views.NotificationListView.as_view(), name='list'),
    path('unread-count/', views.unread_count, name='unread-count'),
    path('mark-read/<uuid:pk>/', views.mark_read, name='mark-read'),
    path('mark-all-read/', views.mark_all_read, name='mark-all-read'),

    # ── Message views ───────────────────────────────────────────────────────
    path('messages/', views.MessageInboxView.as_view(), name='inbox'),
    path('messages/compose/', views.ComposeMessageView.as_view(), name='compose'),
    path('messages/<uuid:pk>/', views.MessageThreadView.as_view(), name='thread'),
    path('messages/<uuid:pk>/reply/', views.ReplyMessageView.as_view(), name='reply'),
]
```

- [ ] **Step 5: Run tests — verify they PASS**

```
py manage.py test notifications.tests.NotificationListViewTest notifications.tests.MessageViewTest -v 2
```

Expected: `OK` — all 11 tests pass.

- [ ] **Step 6: Run full notifications test suite**

```
py manage.py test notifications -v 2
```

Expected: `OK` — all tests pass.

- [ ] **Step 7: Commit**

```
git add notifications/views.py notifications/urls.py notifications/tests.py
git commit -m "feat(notifications): add page views for notification list and message inbox"
```

---

## Task 8: HTMX Partial Templates

**Files:**
- Create: `templates/notifications/_bell_badge.html`
- Create: `templates/notifications/_toast.html`
- Create: `templates/notifications/_notification_item.html`

- [ ] **Step 1: Create `templates/notifications/_bell_badge.html`**

This is the self-polling bell button. It replaces itself on each HTMX poll (outerHTML swap).

```html
{# templates/notifications/_bell_badge.html #}
{# Called by HTMX every 30s. Returned as outerHTML replacement of #notification-badge. #}
{# If 'toast' context var is set, also injects _toast.html via OOB into #toast-container. #}

<div id="notification-badge"
     hx-get="{% url 'notifications:unread-count' %}"
     hx-trigger="every 30s [!document.hidden]"
     hx-swap="outerHTML"
     class="relative">
    <a href="{% url 'notifications:list' %}"
       class="p-2 text-slate-500 hover:text-brand-600 transition relative flex items-center justify-center">
        <i class="ph-duotone ph-bell text-2xl"></i>
        {% if unread_count > 0 %}
        <span class="absolute top-1 right-1 min-w-[18px] h-[18px] px-0.5
                     bg-red-500 border-2 border-white rounded-full
                     text-white text-[9px] flex items-center justify-center font-bold">
            {{ unread_count }}
        </span>
        {% endif %}
    </a>
</div>

{% if toast %}
{# OOB swap — injects toast into #toast-container in the header #}
<div id="toast-container" hx-swap-oob="true">
    {% include 'notifications/_toast.html' with toast=toast %}
</div>
{% endif %}
```

- [ ] **Step 2: Create `templates/notifications/_toast.html`**

```html
{# templates/notifications/_toast.html #}
{# Alpine.js auto-dismisses after 5 seconds. #}

<div x-data="{ show: true }"
     x-init="setTimeout(() => show = false, 5000)"
     x-show="show"
     x-transition:enter="transition ease-out duration-300"
     x-transition:enter-start="opacity-0 translate-y-2"
     x-transition:enter-end="opacity-100 translate-y-0"
     x-transition:leave="transition ease-in duration-200"
     x-transition:leave-start="opacity-100"
     x-transition:leave-end="opacity-0"
     class="flex items-center gap-3 bg-slate-800 text-white text-sm px-4 py-2.5 rounded-xl shadow-lg">
    <i class="ph-duotone ph-bell-ringing text-brand-400 text-lg flex-shrink-0"></i>
    <a href="{{ toast.url }}" class="hover:underline line-clamp-1">{{ toast.title }}</a>
    <button @click="show = false" class="text-slate-400 hover:text-white ml-1">
        <i class="ph-bold ph-x text-xs"></i>
    </button>
</div>
```

- [ ] **Step 3: Create `templates/notifications/_notification_item.html`**

```html
{# templates/notifications/_notification_item.html #}
{# Used inside list.html loop. Also returned by mark_read view for HTMX swap. #}

<div id="notif-{{ notification.pk }}"
     class="flex items-start gap-3 p-4 rounded-xl border transition
            {% if notification.is_read %}border-slate-100 bg-white{% else %}border-brand-100 bg-brand-50{% endif %}">

    <div class="flex-shrink-0 mt-0.5">
        {% if notification.notification_type == 'STATUS_CHANGE' %}
            <i class="ph-duotone ph-arrows-clockwise text-xl text-brand-500"></i>
        {% elif notification.notification_type == 'MESSAGE' %}
            <i class="ph-duotone ph-envelope text-xl text-indigo-500"></i>
        {% else %}
            <i class="ph-duotone ph-chat-dots text-xl text-teal-500"></i>
        {% endif %}
    </div>

    <div class="flex-1 min-w-0">
        <p class="text-sm font-semibold text-slate-800 leading-snug line-clamp-2">
            {% if notification.url %}
            <a href="{{ notification.url }}" class="hover:text-brand-600">{{ notification.title }}</a>
            {% else %}
            {{ notification.title }}
            {% endif %}
        </p>
        <p class="text-xs text-slate-400 mt-1">{{ notification.created_at|timesince }} مضت</p>
    </div>

    {% if not notification.is_read %}
    <button hx-post="{% url 'notifications:mark-read' pk=notification.pk %}"
            hx-swap="outerHTML"
            hx-target="#notif-{{ notification.pk }}"
            class="flex-shrink-0 text-xs text-brand-600 hover:underline whitespace-nowrap">
        تحديد كمقروء
    </button>
    {% endif %}
</div>
```

- [ ] **Step 4: Verify templates are found by running the server and hitting the URL**

```
py manage.py runserver
```

Navigate to `http://127.0.0.1:8000/notifications/unread-count/` while logged in.
Expected: response contains `id="notification-badge"`.

- [ ] **Step 5: Commit**

```
git add templates/notifications/
git commit -m "feat(notifications): add HTMX partial templates (bell badge, toast, item)"
```

---

## Task 9: Full Page Templates

**Files:**
- Create: `templates/notifications/list.html`
- Create: `templates/notifications/messages_inbox.html`
- Create: `templates/notifications/message_thread.html`

- [ ] **Step 1: Create `templates/notifications/list.html`**

```html
{# templates/notifications/list.html #}
{% extends "base.html" %}
{% block title %}الإشعارات — AP PLUS{% endblock %}
{% block header_title %}الإشعارات{% endblock %}

{% block content %}
<div class="max-w-2xl mx-auto space-y-4">

    {# Header row #}
    <div class="flex items-center justify-between">
        <h2 class="text-xl font-bold text-slate-800">إشعاراتي</h2>
        <div class="flex items-center gap-3">
            {# Filter tabs #}
            <a href="?filter=all"
               class="text-sm font-medium px-3 py-1.5 rounded-lg transition
                      {% if active_filter != 'unread' %}bg-brand-600 text-white{% else %}text-slate-500 hover:bg-slate-100{% endif %}">
                الكل
            </a>
            <a href="?filter=unread"
               class="text-sm font-medium px-3 py-1.5 rounded-lg transition
                      {% if active_filter == 'unread' %}bg-brand-600 text-white{% else %}text-slate-500 hover:bg-slate-100{% endif %}">
                غير مقروء
            </a>
            {# Mark all read #}
            <form method="post" action="{% url 'notifications:mark-all-read' %}">
                {% csrf_token %}
                <button type="submit"
                        class="text-sm text-slate-500 hover:text-brand-600 transition">
                    تحديد الكل كمقروء
                </button>
            </form>
        </div>
    </div>

    {# Notification list #}
    {% if notifications %}
    <div class="space-y-2">
        {% for notification in notifications %}
            {% include 'notifications/_notification_item.html' %}
        {% endfor %}
    </div>
    {% else %}
    <div class="text-center py-16 text-slate-400">
        <i class="ph-duotone ph-bell-slash text-5xl mb-3 block"></i>
        <p class="text-sm">لا توجد إشعارات</p>
    </div>
    {% endif %}

    {# Link to messages #}
    <div class="pt-4 text-center">
        <a href="{% url 'notifications:inbox' %}"
           class="text-sm text-brand-600 hover:underline inline-flex items-center gap-1">
            <i class="ph-duotone ph-envelope"></i>
            الانتقال إلى صندوق الرسائل
        </a>
    </div>

</div>
{% endblock %}
```

- [ ] **Step 2: Create `templates/notifications/messages_inbox.html`**

```html
{# templates/notifications/messages_inbox.html #}
{% extends "base.html" %}
{% block title %}صندوق الرسائل — AP PLUS{% endblock %}
{% block header_title %}صندوق الرسائل{% endblock %}

{% block content %}
<div class="max-w-3xl mx-auto space-y-4">

    {# Header #}
    <div class="flex items-center justify-between">
        <h2 class="text-xl font-bold text-slate-800">صندوق الرسائل</h2>
        {% if request.user.role in 'BROKER_ADMIN,BROKER_STAFF,SUPER_ADMIN' %}
        <a href="{% url 'notifications:compose' %}"
           class="inline-flex items-center gap-2 bg-brand-600 text-white text-sm font-medium
                  px-4 py-2 rounded-xl hover:bg-brand-700 transition">
            <i class="ph-bold ph-pencil-simple-line"></i>
            رسالة جديدة
        </a>
        {% endif %}
    </div>

    {% if compose_mode %}
    {# ─── Compose Form ─── #}
    <div class="bg-white border border-slate-200 rounded-2xl p-6 space-y-4">
        <h3 class="text-lg font-bold text-slate-800">إرسال رسالة جديدة</h3>
        {% if error %}
        <p class="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{{ error }}</p>
        {% endif %}
        <form method="post" action="{% url 'notifications:compose' %}" enctype="multipart/form-data" class="space-y-4">
            {% csrf_token %}
            <div>
                <label class="text-sm font-medium text-slate-700 block mb-1">المستلم</label>
                <select name="recipient" required
                        class="w-full border border-slate-300 rounded-xl px-3 py-2.5 text-sm
                               focus:outline-none focus:ring-2 focus:ring-brand-500">
                    <option value="">— اختر المستلم —</option>
                    {% for u in recipients %}
                    <option value="{{ u.pk }}">{{ u.get_full_name|default:u.username }} ({{ u.get_role_display }})</option>
                    {% endfor %}
                </select>
            </div>
            <div>
                <label class="text-sm font-medium text-slate-700 block mb-1">الموضوع</label>
                <input type="text" name="subject" required maxlength="300"
                       class="w-full border border-slate-300 rounded-xl px-3 py-2.5 text-sm
                              focus:outline-none focus:ring-2 focus:ring-brand-500">
            </div>
            <div>
                <label class="text-sm font-medium text-slate-700 block mb-1">الرسالة</label>
                <textarea name="body" required rows="5"
                          class="w-full border border-slate-300 rounded-xl px-3 py-2.5 text-sm
                                 focus:outline-none focus:ring-2 focus:ring-brand-500"></textarea>
            </div>
            <div>
                <label class="text-sm font-medium text-slate-700 block mb-1">مرفق (اختياري)</label>
                <input type="file" name="attachment"
                       class="text-sm text-slate-600 file:mr-3 file:py-1.5 file:px-3
                              file:rounded-lg file:border-0 file:text-sm file:bg-brand-50
                              file:text-brand-700 hover:file:bg-brand-100">
            </div>
            <div class="flex items-center gap-3">
                <button type="submit"
                        class="bg-brand-600 text-white text-sm font-medium px-5 py-2.5 rounded-xl hover:bg-brand-700 transition">
                    إرسال
                </button>
                <a href="{% url 'notifications:inbox' %}" class="text-sm text-slate-500 hover:text-slate-700">إلغاء</a>
            </div>
        </form>
    </div>
    {% else %}
    {# ─── Inbox List ─── #}
    {% if inbox %}
    <div class="space-y-2">
        {% for msg in inbox %}
        <a href="{% url 'notifications:thread' pk=msg.pk %}"
           class="flex items-start gap-4 p-4 bg-white rounded-2xl border transition hover:border-brand-300
                  {% if not msg.is_read and msg.recipient == request.user %}border-brand-200 bg-brand-50{% else %}border-slate-100{% endif %}">
            <div class="h-10 w-10 rounded-full bg-brand-100 flex items-center justify-center
                        text-brand-700 font-bold flex-shrink-0 text-sm">
                {{ msg.sender.first_name|first|default:msg.sender.username|first }}
            </div>
            <div class="flex-1 min-w-0">
                <div class="flex items-center justify-between gap-2">
                    <p class="text-sm font-semibold text-slate-800 truncate">{{ msg.subject }}</p>
                    <span class="text-xs text-slate-400 whitespace-nowrap flex-shrink-0">
                        {{ msg.created_at|timesince }} مضت
                    </span>
                </div>
                <p class="text-xs text-slate-500 mt-0.5">
                    من: {{ msg.sender.get_full_name|default:msg.sender.username }}
                </p>
                <p class="text-xs text-slate-400 mt-1 line-clamp-1">{{ msg.body }}</p>
            </div>
            {% if not msg.is_read and msg.recipient == request.user %}
            <span class="flex-shrink-0 h-2.5 w-2.5 bg-brand-500 rounded-full mt-2"></span>
            {% endif %}
        </a>
        {% endfor %}
    </div>
    {% else %}
    <div class="text-center py-16 text-slate-400">
        <i class="ph-duotone ph-envelope-open text-5xl mb-3 block"></i>
        <p class="text-sm">صندوق الرسائل فارغ</p>
    </div>
    {% endif %}
    {% endif %}

</div>
{% endblock %}
```

- [ ] **Step 3: Create `templates/notifications/message_thread.html`**

```html
{# templates/notifications/message_thread.html #}
{% extends "base.html" %}
{% block title %}{{ root.subject }} — AP PLUS{% endblock %}
{% block header_title %}{{ root.subject }}{% endblock %}

{% block content %}
<div class="max-w-2xl mx-auto space-y-4">

    {# Back link #}
    <a href="{% url 'notifications:inbox' %}"
       class="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-brand-600 transition">
        <i class="ph-bold ph-arrow-right"></i>
        صندوق الرسائل
    </a>

    {# Root message #}
    <div class="bg-white border border-slate-200 rounded-2xl p-6 space-y-3">
        <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
                <div class="h-9 w-9 rounded-full bg-brand-100 flex items-center justify-center
                            text-brand-700 font-bold text-sm">
                    {{ root.sender.first_name|first|default:root.sender.username|first }}
                </div>
                <div>
                    <p class="text-sm font-semibold text-slate-800">
                        {{ root.sender.get_full_name|default:root.sender.username }}
                    </p>
                    <p class="text-xs text-slate-400">{{ root.created_at|date:"Y/m/d H:i" }}</p>
                </div>
            </div>
            <span class="text-xs text-slate-400 bg-slate-100 px-2 py-1 rounded-lg">
                {{ root.sender.get_role_display }}
            </span>
        </div>
        <hr class="border-slate-100">
        <p class="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">{{ root.body }}</p>
        {% if root.attachment %}
        <a href="{{ root.attachment.url }}"
           class="inline-flex items-center gap-1.5 text-xs text-brand-600 hover:underline mt-1">
            <i class="ph-duotone ph-paperclip"></i>
            تحميل المرفق
        </a>
        {% endif %}
    </div>

    {# Replies #}
    {% for reply in replies %}
    <div class="rounded-2xl p-5 space-y-2 border
                {% if reply.sender == request.user %}bg-brand-50 border-brand-100 mr-8{% else %}bg-white border-slate-100 ml-8{% endif %}">
        <div class="flex items-center gap-2">
            <div class="h-8 w-8 rounded-full bg-slate-200 flex items-center justify-center
                        text-slate-600 font-bold text-xs">
                {{ reply.sender.first_name|first|default:reply.sender.username|first }}
            </div>
            <div>
                <p class="text-xs font-semibold text-slate-700">
                    {{ reply.sender.get_full_name|default:reply.sender.username }}
                </p>
                <p class="text-[10px] text-slate-400">{{ reply.created_at|timesince }} مضت</p>
            </div>
        </div>
        <p class="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed pr-10">{{ reply.body }}</p>
    </div>
    {% endfor %}

    {# Reply form #}
    <div class="bg-white border border-slate-200 rounded-2xl p-5 space-y-3">
        <h3 class="text-sm font-semibold text-slate-700">ردّ على هذه المحادثة</h3>
        <form method="post" action="{% url 'notifications:reply' pk=root.pk %}">
            {% csrf_token %}
            <textarea name="body" rows="3" required placeholder="اكتب ردّك هنا..."
                      class="w-full border border-slate-300 rounded-xl px-3 py-2.5 text-sm mb-3
                             focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"></textarea>
            <button type="submit"
                    class="bg-brand-600 text-white text-sm font-medium px-5 py-2 rounded-xl
                           hover:bg-brand-700 transition inline-flex items-center gap-2">
                <i class="ph-bold ph-paper-plane-tilt"></i>
                إرسال الرد
            </button>
        </form>
    </div>

</div>
{% endblock %}
```

- [ ] **Step 4: Manually verify pages load**

```
py manage.py runserver
```

- Visit `http://127.0.0.1:8000/notifications/` — notification list page renders.
- Visit `http://127.0.0.1:8000/notifications/messages/` — inbox page renders.
- As a BROKER_ADMIN user, visit `http://127.0.0.1:8000/notifications/messages/compose/` — compose form renders.

- [ ] **Step 5: Commit**

```
git add templates/notifications/
git commit -m "feat(notifications): add full page templates (list, inbox, thread)"
```

---

## Task 10: Header Integration

**Files:**
- Modify: `templates/includes/header.html`
- Modify: `templates/base.html`

- [ ] **Step 1: Replace the static bell button in `templates/includes/header.html`**

Find this block in the file (inside `{% if user.is_authenticated %}`):

```html
        <!-- Notifications -->
        <div class="relative">
            <button class="p-2 text-slate-500 hover:text-brand-600 transition">
                <i class="ph-duotone ph-bell text-2xl"></i>
                <span
                    class="absolute top-1.5 right-1.5 h-2.5 w-2.5 bg-red-500 border-2 border-white rounded-full"></span>
            </button>
        </div>
```

Replace it with:

```html
        <!-- Notifications: HTMX-powered bell badge (self-polling) -->
        {% include 'notifications/_bell_badge.html' with unread_count=request.user.notifications.filter.count %}
```

Wait — `filter` on a related manager can't be called in templates this way. Instead, pass the count via a context processor or use a simpler template tag approach.

**Correct approach:** Use a `with` tag with a view-computed count. But `header.html` is included in `base.html` which doesn't have a view context. The solution is to make `_bell_badge.html` self-contained: on initial render, HTMX immediately fetches the count (via `hx-trigger="load, every 30s"`).

Replace the static bell with:

```html
        <!-- Notifications: HTMX self-loading bell badge -->
        <div id="notification-badge"
             hx-get="{% url 'notifications:unread-count' %}"
             hx-trigger="load, every 30s [!document.hidden]"
             hx-swap="outerHTML"
             class="relative">
            {# Placeholder until first HTMX load #}
            <a href="{% url 'notifications:list' %}"
               class="p-2 text-slate-500 hover:text-brand-600 transition flex items-center justify-center">
                <i class="ph-duotone ph-bell text-2xl"></i>
            </a>
        </div>
```

- [ ] **Step 2: Update `templates/includes/header.html` — make `#toast-container` ready for OOB injection**

Find:

```html
    <!-- Center Toast Area (Placeholder for messages) -->
    <div id="toast-container" class="hidden md:flex items-center justify-center">
        <!-- Messages will be injected here via HTMX or Alpine -->
    </div>
```

Replace `hidden md:flex` with `flex` and remove the comment (HTMX OOB will inject content):

```html
    <!-- Center Toast Area — HTMX OOB target for notification toasts -->
    <div id="toast-container" class="flex items-center justify-center min-h-[40px]">
    </div>
```

- [ ] **Step 3: Add JS helper for `?since=` parameter in `templates/base.html`**

Find `</body>` (or the last `</script>` block before `</body>`) and add before it:

```html
    <script>
        // Send ?since=<unix_timestamp> with each polling request so the server can detect
        // new notifications since the last check and inject a toast via HTMX OOB.
        (function () {
            document.body.addEventListener('htmx:configRequest', function (event) {
                var path = event.detail.path || '';
                if (path.indexOf('/notifications/unread-count/') !== -1) {
                    var since = sessionStorage.getItem('notif_last_check') || '0';
                    event.detail.parameters['since'] = since;
                }
            });
            document.body.addEventListener('htmx:afterRequest', function (event) {
                var path = (event.detail.pathInfo && event.detail.pathInfo.requestPath) || '';
                if (path.indexOf('/notifications/unread-count/') !== -1) {
                    sessionStorage.setItem(
                        'notif_last_check',
                        Math.floor(Date.now() / 1000).toString()
                    );
                }
            });
        })();
    </script>
```

- [ ] **Step 4: Manual end-to-end verification**

Start the server: `py manage.py runserver`

1. Log in as any user → bell badge appears in the header.
2. Open DevTools Network tab → confirm `/notifications/unread-count/` is called every 30s.
3. Create a `Notification` record in Django Admin for the logged-in user → within 30s, the badge shows the count.
4. Click the bell → navigates to `/notifications/` list page.
5. Click "تحديد كمقروء" on a notification → the item updates in place (HTMX swap).
6. Log in as BROKER_ADMIN, send a message to a MEMBER → MEMBER's badge updates with the count.
7. Log in as MEMBER, open the message thread → thread renders, reply form works.

- [ ] **Step 5: Commit**

```
git add templates/includes/header.html templates/base.html
git commit -m "feat(notifications): integrate bell badge and toast into header"
```

---

## Final Verification

- [ ] **Run the full test suite**

```
py manage.py test notifications -v 2
```

Expected: `OK` — all tests pass with zero failures or errors.

- [ ] **Run Django system check**

```
py manage.py check
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Final commit summary**

The feature spans these commits (verify with `git log --oneline`):
1. `feat(notifications): scaffold app skeleton`
2. `feat(notifications): add Notification and Message models`
3. `feat(notifications): add admin for Notification and Message`
4. `feat(notifications): add NotificationService with routing logic`
5. `feat(notifications): add signals for ServiceRequest and Claim status changes`
6. `feat(notifications): add HTMX partial views (unread-count, mark-read)`
7. `feat(notifications): add page views for notification list and message inbox`
8. `feat(notifications): add HTMX partial templates (bell badge, toast, item)`
9. `feat(notifications): add full page templates (list, inbox, thread)`
10. `feat(notifications): integrate bell badge and toast into header`
