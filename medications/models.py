import uuid
import calendar
import datetime
import os
from django.db import models, transaction
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils.text import get_valid_filename
from django.core.exceptions import ValidationError


def _add_months(d, months):
    """إضافة عدد من الأشهر إلى تاريخ بشكل آمن."""
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return d.replace(year=year, month=month, day=day)


def medication_file_upload_path(instance, filename):
    """مسار ديناميكي للملفات: medications/docs/MED-2026-00001/filename"""
    ref = instance.medication_request.reference or "unsorted"
    filename = get_valid_filename(filename)
    _, ext = os.path.splitext(filename)
    safe_name = f"{uuid.uuid4().hex}{ext}"
    return os.path.join('medications', 'docs', ref, safe_name)


# ====================================================
# 1. طلب الأدوية (المرتبط بالطلب الأساسي)
# ====================================================
class MedicationRequest(models.Model):
    class Status(models.TextChoices):
        PROCESSING = 'PROCESSING', _('Under Processing')
        ACTIVE     = 'ACTIVE',     _('Active')
        COMPLETED  = 'COMPLETED',  _('Completed')
        CANCELLED  = 'CANCELLED',  _('Cancelled')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(
        _("Reference"),
        max_length=20,
        unique=True,
        editable=False,
        db_index=True,
    )

    service_request = models.OneToOneField(
        'service_requests.ServiceRequest',
        on_delete=models.PROTECT,
        related_name='medication_details',
        verbose_name=_("Original Service Request"),
    )

    # القواعد الطبية
    prescription_date = models.DateField(_("Prescription Date"), db_index=True)
    prescription_validity_months = models.PositiveIntegerField(
        _("Prescription Validity (Months)"),
        default=6,
        help_text=_("Number of months the prescription is valid (default: 6)"),
    )
    interval_months = models.PositiveIntegerField(
        _("Dispense Interval (Months)"),
        help_text=_("e.g., 1 for Monthly, 3 for Quarterly"),
    )
    total_duration_months = models.PositiveIntegerField(
        _("Total Duration (Months)"),
        help_text=_("Total treatment duration, e.g., 6 or 12"),
    )

    # عنوان التسليم (JSON منظم)
    delivery_address_snapshot = models.JSONField(
        _("Delivery Address Snapshot"),
        default=dict,
        help_text=_("Frozen delivery address at time of transfer"),
    )

    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=Status.choices,
        default=Status.PROCESSING,
        db_index=True,
    )

    broker_note = models.TextField(_("Broker Note"), blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_medication_requests',
    )

    class Meta:
        verbose_name = _("Medication Request")
        verbose_name_plural = _("Medication Requests")
        ordering = ['-created_at']
        permissions = [
            ("can_transfer_to_medications",  "Can transfer service request to medications"),
            ("can_view_medication_dashboard", "Can view medications dashboard"),
            ("can_schedule_refill",           "Can schedule medication refill"),
            ("can_approve_refill",            "Can approve medication refill"),
            ("can_dispense_medication",       "Can dispense medication (Pharmacy)"),
            ("can_view_refill_alerts",        "Can view refill and prescription alerts"),
        ]

    def __str__(self):
        return self.reference or str(self.id)

    @property
    def prescription_expiry_date(self):
        return _add_months(self.prescription_date, self.prescription_validity_months)

    @property
    def max_cycles(self):
        if self.interval_months and self.interval_months > 0:
            import math
            return math.ceil(self.total_duration_months / self.interval_months)
        return 0

    def save(self, *args, **kwargs):
        if not self.reference:
            with transaction.atomic():
                year = datetime.date.today().year
                last = (
                    MedicationRequest.objects
                    .select_for_update()
                    .filter(reference__startswith=f"MED-{year}")
                    .order_by('-reference')
                    .first()
                )
                new_id = (int(last.reference.split('-')[-1]) + 1) if last else 1
                self.reference = f"MED-{year}-{new_id:05d}"
        super().save(*args, **kwargs)

    def change_status(self, new_status, user, action, note=''):
        allowed = {
            self.Status.PROCESSING: [self.Status.ACTIVE, self.Status.CANCELLED],
            self.Status.ACTIVE:     [self.Status.COMPLETED, self.Status.CANCELLED],
            self.Status.COMPLETED:  [],
            self.Status.CANCELLED:  [],
        }
        if new_status not in allowed.get(self.status, []):
            raise ValidationError(
                _("Invalid status transition from %(from)s to %(to)s.") % {
                    'from': self.status, 'to': new_status
                }
            )
        old = self.status
        self.status = new_status
        self.broker_note = note or self.broker_note
        with transaction.atomic():
            self.save(update_fields=['status', 'broker_note', 'updated_at'])
            MedicationStatusLog.objects.create(
                medication_request=self,
                refill=None,
                from_status=old,
                to_status=new_status,
                action=action,
                reason=note,
                user=user,
            )


# ====================================================
# 2. دورات الصرف المجدولة (Refills)
# ====================================================
class MedicationRefill(models.Model):
    class RefillStatus(models.TextChoices):
        PENDING          = 'PENDING',          _('Pending Approval')
        APPROVED         = 'APPROVED',         _('Approved')
        PROCESSING       = 'PROCESSING',       _('Processing at Pharmacy')
        OUT_FOR_DELIVERY = 'OUT_FOR_DELIVERY', _('Out for Delivery')
        DELIVERED        = 'DELIVERED',        _('Delivered')
        CANCELLED        = 'CANCELLED',        _('Cancelled')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    medication_request = models.ForeignKey(
        MedicationRequest,
        on_delete=models.CASCADE,
        related_name='refills',
    )
    partner = models.ForeignKey(
        'partners.Partner',
        on_delete=models.PROTECT,
        null=True, blank=True,
        verbose_name=_("Dispensing Pharmacy"),
    )

    cycle_number   = models.PositiveIntegerField(_("Cycle Number"))
    scheduled_date = models.DateField(_("Scheduled Date"), db_index=True)
    actual_dispense_date = models.DateTimeField(_("Actual Dispense Date"), null=True, blank=True)
    notes = models.TextField(_("Notes"), blank=True)

    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=RefillStatus.choices,
        default=RefillStatus.PENDING,
        db_index=True,
    )

    # Audit
    scheduled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='scheduled_refills',
        verbose_name=_("Scheduled By"),
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='approved_refills',
        verbose_name=_("Approved By"),
    )
    approved_at = models.DateTimeField(_("Approved At"), null=True, blank=True)

    class Meta:
        ordering = ['scheduled_date']
        verbose_name = _('Medication Refill')
        verbose_name_plural = _('Medication Refills')
        unique_together = ('medication_request', 'cycle_number')

    def __str__(self):
        return f"Refill #{self.cycle_number} — {self.scheduled_date}"

    def clean(self):
        if self.cycle_number and self.medication_request_id:
            max_c = self.medication_request.max_cycles
            if max_c and self.cycle_number > max_c:
                raise ValidationError(
                    _("Cycle number %(n)s exceeds the maximum allowed cycles (%(max)s).") % {
                        'n': self.cycle_number, 'max': max_c
                    }
                )

    def change_status(self, new_status, user, action_name, reason=""):
        allowed_transitions = {
            self.RefillStatus.PENDING:          [self.RefillStatus.APPROVED,         self.RefillStatus.CANCELLED],
            self.RefillStatus.APPROVED:         [self.RefillStatus.PROCESSING,        self.RefillStatus.CANCELLED],
            self.RefillStatus.PROCESSING:       [self.RefillStatus.OUT_FOR_DELIVERY,  self.RefillStatus.CANCELLED],
            self.RefillStatus.OUT_FOR_DELIVERY: [self.RefillStatus.DELIVERED,         self.RefillStatus.CANCELLED],
            self.RefillStatus.DELIVERED:        [],
            self.RefillStatus.CANCELLED:        [],
        }
        if new_status not in allowed_transitions.get(self.status, []):
            raise ValidationError(
                _("Invalid transition from %(from)s to %(to)s.") % {
                    'from': self.status, 'to': new_status
                }
            )
        old_status = self.status
        self.status = new_status
        with transaction.atomic():
            update_fields = ['status']
            if new_status == self.RefillStatus.APPROVED:
                from django.utils import timezone
                self.approved_by = user
                self.approved_at = timezone.now()
                update_fields += ['approved_by', 'approved_at']
            if new_status == self.RefillStatus.DELIVERED:
                from django.utils import timezone
                self.actual_dispense_date = timezone.now()
                update_fields.append('actual_dispense_date')
            self.save(update_fields=update_fields)
            MedicationStatusLog.objects.create(
                refill=self,
                medication_request=None,
                from_status=old_status,
                to_status=new_status,
                action=action_name,
                reason=reason,
                user=user,
            )


# ====================================================
# 3. مرفقات طلب الدواء
# ====================================================
class MedicationAttachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    medication_request = models.ForeignKey(
        MedicationRequest,
        on_delete=models.CASCADE,
        related_name='attachments',
    )
    original_attachment = models.ForeignKey(
        'service_requests.RequestAttachment',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='medication_copies',
        verbose_name=_("Original Attachment"),
    )
    file = models.FileField(_("File"), upload_to=medication_file_upload_path)
    description = models.CharField(_("Description"), max_length=100, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Medication Attachment")
        verbose_name_plural = _("Medication Attachments")
        ordering = ['uploaded_at']

    def __str__(self):
        return self.description or self.file.name


# ====================================================
# 4. نظام المحادثات الداخلي والعام
# ====================================================
class MedicationComment(models.Model):
    class Visibility(models.TextChoices):
        GENERAL  = 'GENERAL',  _('General')
        INTERNAL = 'INTERNAL', _('Internal (Broker & Pharmacy Only)')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    medication_request = models.ForeignKey(MedicationRequest, on_delete=models.CASCADE, related_name='comments')
    author  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    message = models.TextField(_("Comment Message"))
    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.GENERAL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = _("Medication Comment")
        verbose_name_plural = _("Medication Comments")

    def __str__(self):
        return f"{self.author} — {self.created_at:%Y-%m-%d}"


# ====================================================
# 5. سجل التتبع الأمني والتشغيلي (Audit Trail)
# ====================================================
class MedicationStatusLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # مرتبط بدورة الصرف أو بالطلب مباشرة (أحدهما مطلوب)
    refill = models.ForeignKey(
        MedicationRefill,
        on_delete=models.CASCADE,
        related_name='status_logs',
        null=True, blank=True,
    )
    medication_request = models.ForeignKey(
        MedicationRequest,
        on_delete=models.CASCADE,
        related_name='status_logs',
        null=True, blank=True,
    )

    from_status = models.CharField(max_length=50)
    to_status   = models.CharField(max_length=50)
    action      = models.CharField(max_length=50)
    reason      = models.TextField(blank=True)
    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Medication Status Log")
        verbose_name_plural = _("Medication Status Logs")