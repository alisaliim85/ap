import uuid
from django.db import models, transaction
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

# ====================================================
# 1. طلب الأدوية (المرتبط بالطلب الأساسي)
# ====================================================
class MedicationRequest(models.Model):
    class Status(models.TextChoices):
        PROCESSING = 'PROCESSING', _('Under Processing')
        ACTIVE = 'ACTIVE', _('Active (Refills Generated)')
        COMPLETED = 'COMPLETED', _('Completed')
        CANCELLED = 'CANCELLED', _('Cancelled')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    service_request = models.OneToOneField(
        'service_requests.ServiceRequest', # تأكد من اسم التطبيق لديك
        on_delete=models.PROTECT,
        related_name='medication_details',
        verbose_name=_("Original Service Request")
    )
    
    # القواعد الطبية الصارمة
    prescription_date = models.DateField(_("Prescription Date"))
    interval_months = models.PositiveIntegerField(
        _("Dispense Interval (Months)"), 
        help_text=_("e.g., 1 for Monthly, 3 for Quarterly")
    )
    total_duration_months = models.PositiveIntegerField(
        _("Total Duration (Months)"),
        help_text=_("Total treatment duration, e.g., 6 or 12")
    )

    # حفظ لقطة العنوان اللوجستي
    delivery_address_snapshot = models.TextField(_("Delivery Address Snapshot"))
    
    status = models.CharField(
        _("Status"), 
        max_length=20,
        choices=Status.choices, 
        default=Status.PROCESSING
    )

    # التدقيق الأمني (Audit Fields)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT,
        related_name='created_medication_requests'
    )

    class Meta:
        verbose_name = _("Medication Request")
        verbose_name_plural = _("Medication Requests")
        ordering = ['-created_at']

    def __str__(self):
        return f"Medication For SR: {self.service_request_id}"


# ====================================================
# 2. دورات الصرف المجدولة (Refills)
# ====================================================
class MedicationRefill(models.Model):
    class RefillStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        PROCESSING = 'PROCESSING', _('Processing at Pharmacy')
        OUT_FOR_DELIVERY = 'OUT_FOR_DELIVERY', _('Out for Delivery')
        DELIVERED = 'DELIVERED', _('Delivered')
        CANCELLED = 'CANCELLED', _('Cancelled')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    medication_request = models.ForeignKey(
        MedicationRequest, 
        on_delete=models.CASCADE, 
        related_name='refills'
    )
    partner = models.ForeignKey(
        'partners.Partner', 
        on_delete=models.PROTECT, 
        null=True, blank=True,
        verbose_name=_("Dispensing Pharmacy")
    )

    cycle_number = models.PositiveIntegerField(_("Cycle Number"))
    scheduled_date = models.DateField(_("Scheduled Date"))
    actual_dispense_date = models.DateTimeField(_("Actual Dispense Date"), null=True, blank=True)
    
    status = models.CharField(
        _("Status"), 
        max_length=20,
        choices=RefillStatus.choices, 
        default=RefillStatus.PENDING
    )

    class Meta:
        ordering = ['scheduled_date']
        verbose_name = _('Medication Refill')
        verbose_name_plural = _('Medication Refills')
        unique_together = ('medication_request', 'cycle_number')

    def __str__(self):
        return f"Refill #{self.cycle_number} - {self.scheduled_date}"

    # الآلية الخفيفة والآمنة لتغيير الحالة (Lightweight State Machine)
    def change_status(self, new_status, user, action_name, reason=""):
        allowed_transitions = {
            self.RefillStatus.PENDING: [self.RefillStatus.PROCESSING, self.RefillStatus.CANCELLED],
            self.RefillStatus.PROCESSING: [self.RefillStatus.OUT_FOR_DELIVERY, self.RefillStatus.CANCELLED],
            self.RefillStatus.OUT_FOR_DELIVERY: [self.RefillStatus.DELIVERED, self.RefillStatus.CANCELLED],
            self.RefillStatus.DELIVERED: [], 
            self.RefillStatus.CANCELLED: [], 
        }

        if new_status not in allowed_transitions.get(self.status, []):
            raise ValidationError(_(f"Invalid transition from {self.status} to {new_status}"))

        old_status = self.status
        self.status = new_status
        
        with transaction.atomic():
            self.save(update_fields=['status'])
            MedicationStatusLog.objects.create(
                refill=self,
                from_status=old_status,
                to_status=new_status,
                action=action_name,
                reason=reason,
                user=user
            )


# ====================================================
# 3. نظام المحادثات الداخلي والعام
# ====================================================
class MedicationComment(models.Model):
    class Visibility(models.TextChoices):
        GENERAL = 'GENERAL', _('General')
        INTERNAL = 'INTERNAL', _('Internal (Broker & Pharmacy Only)')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    medication_request = models.ForeignKey(MedicationRequest, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    message = models.TextField(_("Comment Message"))
    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.GENERAL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


# ====================================================
# 4. سجل التتبع الأمني والتشغيلي (Audit Trail)
# ====================================================
class MedicationStatusLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    refill = models.ForeignKey(MedicationRefill, on_delete=models.CASCADE, related_name='status_logs')
    from_status = models.CharField(max_length=50)
    to_status = models.CharField(max_length=50)
    action = models.CharField(max_length=50)
    reason = models.TextField(blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']