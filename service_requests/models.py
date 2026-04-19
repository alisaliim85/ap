import uuid
import datetime
import os
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _
from django.utils.text import get_valid_filename
from django.conf import settings


# --- دالة مساعدة لتحديد مسار حفظ المرفقات ---
def request_file_upload_path(instance, filename):
    """
    مسار ديناميكي للملفات: service_requests/docs/REQ-2026-00001/filename.pdf
    """
    req_ref = instance.service_request.reference or "unsorted"
    filename = get_valid_filename(filename)
    _, ext = os.path.splitext(filename)
    safe_filename = f"{uuid.uuid4().hex}{ext}"
    return os.path.join('service_requests', 'docs', req_ref, safe_filename)


# ============================================
# 1. أنواع الطلبات (يعرّفها الـ Superuser)
# ============================================
class RequestType(models.Model):
    """
    نوع الطلب (مثال: اعتراض على رفض، موافقة مسبقة، شكوى... إلخ).
    يحتوي على مخطط الحقول الديناميكية (fields_schema) بصيغة JSON.
    """
    INTEGRATION_CHOICES = [
        ('none', 'لا يوجد'),
        ('chronic', 'إدارة الأمراض المزمنة'),
        ('medication', 'إدارة الأدوية'),
        ('devices', 'إدارة الأجهزة الطبية'),
    ]
    name_ar = models.CharField(_("Name (AR)"), max_length=100)
    name_en = models.CharField(_("Name (EN)"), max_length=100, blank=True)
    integration = models.CharField(
        _("Integration"),
        max_length=20,
        choices=INTEGRATION_CHOICES,
        default='none'
    )

    description = models.TextField(_("Description"), blank=True)
    icon = models.CharField(
        _("Phosphor Icon Class"),
        max_length=50,
        default='ph-file-text',
        help_text=_("Phosphor icon class, e.g. ph-file-text, ph-shield-warning")
    )
    fields_schema = models.JSONField(
        _("Fields Schema"),
        default=list,
        help_text=_(
            'JSON array of field definitions. '
            'Each field: {"name": "...", "label": "...", "type": "text|textarea|date|number|select|checkbox", '
            '"required": true/false, "choices": [{"value":"...", "label":"..."}]}'
        )
    )
    is_active = models.BooleanField(_("Active"), default=True)
    display_order = models.PositiveIntegerField(_("Display Order"), default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Request Type")
        verbose_name_plural = _("Request Types")
        ordering = ['display_order', 'name_ar']

    def __str__(self):
        return self.name_ar


# ============================================
# 2. طلب الخدمة
# ============================================
class ServiceRequest(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        SUBMITTED = 'SUBMITTED', _('Submitted')
        IN_REVIEW = 'IN_REVIEW', _('In Review')
        RETURNED = 'RETURNED', _('Returned (Needs More Info)')
        RESOLVED = 'RESOLVED', _('Resolved')
        REJECTED = 'REJECTED', _('Rejected')

    # المعرّفات
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(_("Reference"), max_length=20, unique=True, editable=False)

    # الربط الأساسي
    request_type = models.ForeignKey(
        RequestType,
        on_delete=models.PROTECT,
        related_name='requests',
        verbose_name=_("Request Type")
    )
    member = models.ForeignKey(
        'members.Member',
        on_delete=models.CASCADE,
        related_name='service_requests',
        verbose_name=_("Member")
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='submitted_service_requests',
        verbose_name=_("Submitted By")
    )
    submitted_on_behalf = models.BooleanField(
        _("Submitted On Behalf"),
        default=False,
        help_text=_("True if HR submitted this on behalf of a member")
    )

    # الحالة
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )

    # البيانات الديناميكية (القيم التي أدخلها المستخدم)
    data = models.JSONField(
        _("Dynamic Field Data"),
        default=dict,
        help_text=_("Stores the dynamic field values as key-value pairs")
    )

    # ملاحظات الوسيط
    broker_note = models.TextField(_("Broker Note / Resolution"), blank=True)

    # التواريخ
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(_("Submitted At"), null=True, blank=True)

    class Meta:
        verbose_name = _("Service Request")
        verbose_name_plural = _("Service Requests")
        ordering = ['-created_at']
        permissions = [
            ("can_submit_service_request", "Can submit new service request"),
            ("can_process_service_request", "Can process/resolve service request as Broker"),
        ]

    def __str__(self):
        return f"{self.reference} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.reference:
            with transaction.atomic():
                year = datetime.date.today().year
                last_req = (
                    ServiceRequest.objects
                    .select_for_update()
                    .filter(reference__startswith=f"REQ-{year}")
                    .order_by('-reference')
                    .first()
                )
                if last_req:
                    last_id = int(last_req.reference.split('-')[-1])
                    new_id = last_id + 1
                else:
                    new_id = 1
                self.reference = f"REQ-{year}-{new_id:05d}"
        super().save(*args, **kwargs)

    # ====================================================
    # Status Transition Methods (Lightweight — No django-fsm)
    # ====================================================
    def log_status_change(self, user, from_status, to_status, action, note=''):
        RequestStatusLog.objects.create(
            service_request=self,
            from_status=from_status,
            to_status=to_status,
            action=action,
            note=note,
            user=user,
        )

    def submit(self, user):
        """DRAFT / RETURNED → SUBMITTED"""
        if self.status not in [self.Status.DRAFT, self.Status.RETURNED]:
            raise ValueError(_("Cannot submit from current status."))
        old = self.status
        self.status = self.Status.SUBMITTED
        from django.utils import timezone
        self.submitted_at = timezone.now()
        self.save()
        self.log_status_change(user, old, self.Status.SUBMITTED, 'submit')

    def start_review(self, user):
        """SUBMITTED → IN_REVIEW"""
        if self.status != self.Status.SUBMITTED:
            raise ValueError(_("Cannot start review from current status."))
        old = self.status
        self.status = self.Status.IN_REVIEW
        self.save()
        self.log_status_change(user, old, self.Status.IN_REVIEW, 'start_review')

    def return_request(self, user, note=''):
        """IN_REVIEW → RETURNED"""
        if self.status != self.Status.IN_REVIEW:
            raise ValueError(_("Cannot return from current status."))
        old = self.status
        self.status = self.Status.RETURNED
        self.broker_note = note
        self.save()
        self.log_status_change(user, old, self.Status.RETURNED, 'return', note)

    def resolve(self, user, note=''):
        """IN_REVIEW → RESOLVED"""
        if self.status != self.Status.IN_REVIEW:
            raise ValueError(_("Cannot resolve from current status."))
        old = self.status
        self.status = self.Status.RESOLVED
        self.broker_note = note
        self.save()
        self.log_status_change(user, old, self.Status.RESOLVED, 'resolve', note)

    def reject(self, user, note=''):
        """IN_REVIEW → REJECTED"""
        if self.status != self.Status.IN_REVIEW:
            raise ValueError(_("Cannot reject from current status."))
        old = self.status
        self.status = self.Status.REJECTED
        self.broker_note = note
        self.save()
        self.log_status_change(user, old, self.Status.REJECTED, 'reject', note)


# ============================================
# 3. مرفقات الطلب
# ============================================
class RequestAttachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    file = models.FileField(upload_to=request_file_upload_path)
    description = models.CharField(max_length=100, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.description or self.file.name


# ============================================
# 4. سجل تغييرات الحالة (Audit Trail)
# ============================================
class RequestStatusLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name='status_logs'
    )
    from_status = models.CharField(max_length=20)
    to_status = models.CharField(max_length=20)
    action = models.CharField(
        max_length=50,
        help_text="submit, start_review, return, resolve, reject"
    )
    note = models.TextField(blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Request Status Log")
        verbose_name_plural = _("Request Status Logs")

    def __str__(self):
        return f"{self.service_request.reference}: {self.from_status} → {self.to_status}"
