# notifications/models.py
import uuid
import datetime
from threading import Lock
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.utils import timezone

# On Windows, consecutive datetime.now() calls can return the same microsecond.
# This monotonic wrapper guarantees strictly-increasing created_at values,
# making ordering by -created_at deterministic in tests and production.
_CLOCK_LOCK = Lock()
_last_clock: datetime.datetime | None = None


# NOTE: This function is referenced by migrations/0001_initial.py as a callable default.
# Do NOT rename it without also squashing/updating the migration.
def _monotonic_now() -> datetime.datetime:
    """Return current time, guaranteed strictly greater than the previous call."""
    global _last_clock
    with _CLOCK_LOCK:
        now = timezone.now()
        if _last_clock is not None and now <= _last_clock:
            now = _last_clock + datetime.timedelta(microseconds=1)
        _last_clock = now
    return now


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
    created_at = models.DateTimeField(default=_monotonic_now, editable=False)

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
    created_at = models.DateTimeField(default=_monotonic_now, editable=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
        ]

    def __str__(self):
        return f"{self.sender} → {self.recipient}: {self.subject[:50]}"
