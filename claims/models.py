import uuid
import datetime
import os
from django.db import models
from django.utils.translation import gettext_lazy as _
from encrypted_model_fields.fields import EncryptedTextField # لتشفير نص التعليقات (حماية إضافية)

# --- دالة مساعدة لتحديد مسار حفظ الملفات ---
def claim_file_upload_path(instance, filename):
    """
    تقوم هذه الدالة بإنشاء مسار ديناميكي للملفات.
    المسار سيكون: claims_docs/CLM-2024-0001/filename.pdf
    """
    # instance here is ClaimAttachment
    # نأتي برقم المطالبة من الجدول الأب
    claim_ref = instance.claim.claim_reference
    
    # في حال (نادراً) تم رفع ملف قبل توليد الرقم، نضعه في مجلد مؤقت
    if not claim_ref:
        claim_ref = "unsorted"
        
    return os.path.join('claims', 'docs', claim_ref, filename)


# --- 1. جدول العملات ---
class Currency(models.Model):
    code = models.CharField(_("Currency Code"), max_length=3, primary_key=True) 
    name_ar = models.CharField(_("Name (AR)"), max_length=50)
    name_en = models.CharField(_("Name (EN)"), max_length=50)
    exchange_rate = models.DecimalField(
        _("Exchange Rate to SAR"), 
        max_digits=10, decimal_places=4, default=1.0000
    )

    def __str__(self):
        return self.code


# --- 2. المطالبة المالية ---
class Claim(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        SUBMITTED = 'SUBMITTED', _('Submitted to HR')
        HR_REVIEW = 'HR_REVIEW', _('Under HR Review')
        RETURN_MISSING_DOCS_HR = 'RETURN_MISSING_DOCS_HR', _('Returned by HR (Missing Docs)')
        BROKER_REVIEW = 'BROKER_REVIEW', _('Under Broker Review')
        RETURN_MISSING_DOCS_BROKER = 'RETURN_MISSING_DOCS_BROKER', _('Returned by Broker (Missing Docs)')
        RE_SUBMITTED = 'RE_SUBMITTED', _('Re-Submitted')
        APPROVED = 'APPROVED', _('Approved')
        REJECTED = 'REJECTED', _('Rejected')
        PAID = 'PAID', _('Paid / Settled')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim_reference = models.CharField(_("Claim Ref"), max_length=20, unique=True, editable=False)
    
    member = models.ForeignKey('members.Member', on_delete=models.CASCADE, related_name='claims')
    status = models.CharField(_("Status"), max_length=30, choices=Status.choices, default=Status.DRAFT)
    
    service_date = models.DateField(_("Service Date"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # البيانات المالية
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, default='SAR')
    amount_original = models.DecimalField(_("Amount (Original Currency)"), max_digits=10, decimal_places=2)
    approved_amount_sar = models.DecimalField(_("Approved Amount (SAR)"), max_digits=10, decimal_places=2, null=True, blank=True)
    
    is_in_patient = models.BooleanField(_("In-Patient (Admission)"), default=False)
    is_international = models.BooleanField(_("Treatment Outside KSA"), default=False)

    rejection_reason = models.TextField(_("Rejection/Return Reason"), blank=True)
    admin_notes = models.TextField(_("Internal Notes"), blank=True)

    class Meta:
        verbose_name = _("Claim Request")
        verbose_name_plural = _("Claim Requests")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.claim_reference} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.claim_reference:
            year = datetime.date.today().year
            last_claim = Claim.objects.filter(claim_reference__startswith=f"CLM-{year}").order_by('claim_reference').last()
            if last_claim:
                last_id = int(last_claim.claim_reference.split('-')[-1])
                new_id = last_id + 1
            else:
                new_id = 1
            self.claim_reference = f"CLM-{year}-{new_id:05d}"
        super().save(*args, **kwargs)


# --- 3. المرفقات (مع المسار الجديد) ---
class ClaimAttachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='attachments')
    
    # هنا استخدمنا الدالة بدلاً من المسار الثابت
    file = models.FileField(upload_to=claim_file_upload_path)
    
    description = models.CharField(max_length=100, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)


# --- 4. التعليقات (الجديد) ---
class ClaimComment(models.Model):
    """
    نظام المحادثات داخل المطالبة
    """
    class Visibility(models.TextChoices):
        GENERAL = 'GENERAL', _('General (User, HR, Broker)')
        INTERNAL = 'INTERNAL', _('Internal (HR & Broker Only)')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='comments')
    
    # من كتب التعليق؟
    author = models.ForeignKey('accounts.User', on_delete=models.PROTECT)
    
    # محتوى التعليق (مشفر لأنه قد يحتوي معلومات طبية)
    message = EncryptedTextField(_("Comment Message"))
    
    # نوع التعليق (هل يظهر للمستخدم أم لا؟)
    visibility = models.CharField(
        _("Visibility"), 
        max_length=10, 
        choices=Visibility.choices, 
        default=Visibility.GENERAL
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on {self.claim.claim_reference}"