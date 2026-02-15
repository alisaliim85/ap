import uuid
import datetime
import os
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from django_fsm import FSMField, transition
from django.utils.text import get_valid_filename
from django.conf import settings



# --- دالة مساعدة لتحديد مسار حفظ الملفات ---
def claim_file_upload_path(instance, filename):
    """
    تقوم هذه الدالة بإنشاء مسار ديناميكي للملفات.
    المسار سيكون: claims_docs/CLM-2024-0001/filename.pdf
    """
    claim_ref = instance.claim.claim_reference or "unsorted"

    filename = get_valid_filename(filename)
    _, ext = os.path.splitext(filename)

    safe_filename = f"{uuid.uuid4().hex}{ext}"

    return os.path.join('claims', 'docs', claim_ref, safe_filename)



# --- 1. جدول العملات ---
class Currency(models.Model):
    code = models.CharField(_("Currency Code"), max_length=3, primary_key=True) 
    name_ar = models.CharField(_("Name (AR)"), max_length=50)
    name_en = models.CharField(_("Name (EN)"), max_length=50)
    exchange_rate = models.DecimalField(
        _("Exchange Rate to SAR"), 
        max_digits=10, decimal_places=4, default=1.0000
    )
    class Meta:
        default_permissions = ('add', 'change', 'delete', 'view')   

    def __str__(self):
        return self.code


# --- 2. المطالبة المالية ---
class Claim(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        
        # مرحلة الـ HR
        SUBMITTED_TO_HR = 'SUBMITTED_TO_HR', _('Submitted to HR')
        RETURNED_BY_HR = 'RETURNED_BY_HR', _('Returned by HR (Missing Docs)')
        
        # مرحلة الوسيط (Broker)
        SUBMITTED_TO_BROKER = 'SUBMITTED_TO_BROKER', _('Submitted to Broker') # وافقت الشركة أو تخطتها
        BROKER_PROCESSING = 'BROKER_PROCESSING', _('Under Broker Processing') # بدأ الوسيط العمل
        RETURNED_BY_BROKER = 'RETURNED_BY_BROKER', _('Returned by Broker') # أعادها الوسيط
        
        # مرحلة شركة التأمين (Insurance)
        SENT_TO_INSURANCE = 'SENT_TO_INSURANCE', _('Sent to Insurance Company')
        INSURANCE_QUERY = 'INSURANCE_QUERY', _('Insurance Query (Docs Needed)')
        APPROVED_BY_INSURANCE = 'APPROVED_BY_INSURANCE', _('Approved by Insurance')
        REJECTED_BY_INSURANCE = 'REJECTED_BY_INSURANCE', _('Rejected by Insurance')
        
        # المرحلة النهائية
        PAID = 'PAID', _('Paid / Settled')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim_reference = models.CharField(_("Claim Ref"), max_length=20, unique=True, editable=False)
    
    member = models.ForeignKey('members.Member', on_delete=models.CASCADE, related_name='claims')
    status = FSMField(
        _("Status"), 
        default=Status.DRAFT, 
        choices=Status.choices, 
        protected=True # يمنع تعديل الحالة يدوياً بالكود، يجب استخدام دوال الانتقال
    )    
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
        permissions = [
            ("can_submit_claim", "Can submit new claim"),
            ("can_approve_hr", "Can approve claim as HR"),
            ("can_reject_hr", "Can return/reject claim as HR"),
            ("can_process_broker", "Can process claim as Broker"),
            ("can_approve_payment", "Can mark claim as Paid"),
            ("can_view_all_claims", "Can view all claims"),
            ("view_sensitive_medical_data", "Can view sensitive medical attachments"),
        ]

    def __str__(self):
        return f"{self.claim_reference} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.claim_reference:
            with transaction.atomic():
                year = datetime.date.today().year

                last_claim = (
                Claim.objects
                .select_for_update()
                .filter(claim_reference__startswith=f"CLM-{year}")
                .order_by('-claim_reference')
                .first()
            )

            if last_claim:
                last_id = int(last_claim.claim_reference.split('-')[-1])
                new_id = last_id + 1
            else:
                new_id = 1

            self.claim_reference = f"CLM-{year}-{new_id:05d}"

        super().save(*args, **kwargs)

    # ====================================================
    # FSM Conditions (الشروط)
    # ====================================================
    def can_bypass_hr(self):
        """فحص إعدادات الشركة: هل نتجاوز الـ HR؟"""
        return self.member.client.get_claim_setting('bypass_hr_review', False)

    def needs_hr_review(self):
        """عكس الشرط السابق"""
        return not self.can_bypass_hr()

    # ====================================================
    # FSM Transitions (الانتقالات)
    # ====================================================
    def log_status_change(self, user, from_status, to_status, action, reason=''):
        ClaimStatusLog.objects.create(
            claim=self,
            from_status=from_status,
            to_status=to_status,
            action=action,
            reason=reason,
            user=user
        )



    # 1. إرسال المطالبة (Submit) - سيناريو A: يوجد HR
    @transition(
        field=status, 
        source=[Status.DRAFT, Status.RETURNED_BY_HR], 
        target=Status.SUBMITTED_TO_HR,
        conditions=[needs_hr_review],
        permission=lambda i, u: u.has_perm('claims.can_submit_claim'),
        custom={'label': _('Submit to HR')}
    )
    def submit_to_hr(self, user):
        # يمكن هنا إرسال إيميل للـ HR
        self.log_status_change(
            user=user,
            from_status=self.status,
            to_status=Status.SUBMITTED_TO_HR,
            action='submit_to_hr',
            reason='',
        )

    # 1. إرسال المطالبة (Submit) - سيناريو B: تجاوز الـ HR مباشرة
    @transition(
        field=status, 
        source=[Status.DRAFT, Status.RETURNED_BY_HR, Status.RETURNED_BY_BROKER], 
        target=Status.SUBMITTED_TO_BROKER,
        conditions=[can_bypass_hr],
        permission=lambda i, u: u.has_perm('claims.can_submit_claim'),
        custom={'label': _('Submit directly to Broker')}
    )
    def submit_direct_to_broker(self, user):
        # إشعار للوسيط مباشرة
        self.log_status_change(
            user=user,
            from_status=self.status,
            to_status=Status.SUBMITTED_TO_BROKER,
            action='submit_direct_to_broker',
            reason='',
        )

    # 2. إجراءات الـ HR
    @transition(
        field=status, 
        source=Status.SUBMITTED_TO_HR, 
        target=Status.SUBMITTED_TO_BROKER,
        permission=lambda i, u: u.has_perm('claims.can_approve_hr'),
        custom={'label': _('HR Approve')}
    )
    def hr_approve(self, user):
        self.log_status_change(
            user=user,
            from_status=self.status,
            to_status=Status.SUBMITTED_TO_BROKER,
            action='hr_approve',
            reason='',
        )

    @transition(
        field=status, 
        source=Status.SUBMITTED_TO_HR, 
        target=Status.RETURNED_BY_HR,
        permission=lambda i, u: u.has_perm('claims.can_reject_hr'),
        custom={'label': _('HR Return')}
    )
    def hr_return(self, user , reason):
        self.rejection_reason = reason
        self.log_status_change(
            user=user,
            from_status=self.status,
            to_status=Status.RETURNED_BY_HR,
            action='hr_return',
            reason=reason,
        )

    # 3. إجراءات الوسيط (الاستلام والبدء)
    @transition(
        field=status, 
        source=Status.SUBMITTED_TO_BROKER, 
        target=Status.BROKER_PROCESSING,
        permission=lambda i, u: u.has_perm('claims.can_process_broker'),
        custom={'label': _('Start Processing')}
    )
    def broker_start_process(self, user):
        self.log_status_change(
            user=user,
            from_status=self.status,
            to_status=Status.BROKER_PROCESSING,
            action='broker_start_process',
            reason='',
        )

    # 4. إعادة الوسيط للمطالبة (للنواقص)
    @transition(
        field=status, 
        source=Status.BROKER_PROCESSING, 
        target=Status.RETURNED_BY_BROKER,
        permission=lambda i, u: u.has_perm('claims.can_process_broker'),
        custom={'label': _('Return to Member (Missing Docs)')}
    )
    def broker_return(self, user, reason):
        self.rejection_reason = reason
        self.log_status_change(
            user=user,
            from_status=self.status,
            to_status=Status.RETURNED_BY_BROKER,
            action='broker_return',
            reason=reason,
        )

    # 5. الإرسال لشركة التأمين
    @transition(
        field=status, 
        source=Status.BROKER_PROCESSING, 
        target=Status.SENT_TO_INSURANCE,
        permission=lambda i, u: u.has_perm('claims.can_process_broker'),
        custom={'label': _('Send to Insurance')}
    )
    def sent_to_insurance(self, user):
        self.log_status_change(
            user=user,
            from_status=self.status,
            to_status=Status.SENT_TO_INSURANCE,
            action='sent_to_insurance',
            reason='',
        )

    # 6. ردود شركة التأمين
    @transition(field=status, source=Status.SENT_TO_INSURANCE, target=Status.INSURANCE_QUERY, permission=lambda i, u: u.has_perm('claims.can_process_broker'))
    def insurance_query(self, user):
        self.log_status_change(
            user=user,
            from_status=self.status,
            to_status=Status.INSURANCE_QUERY,
            action='insurance_query',
            reason='',
        )

    @transition(field=status, source=Status.INSURANCE_QUERY, target=Status.SENT_TO_INSURANCE, permission=lambda i, u: u.has_perm('claims.can_process_broker'))
    def answer_insurance_query(self, user):
        self.log_status_change(
            user=user,
            from_status=self.status,
            to_status=Status.SENT_TO_INSURANCE,
            action='answer_insurance_query',
            reason='',
        )

    @transition(field=status, source=Status.SENT_TO_INSURANCE, target=Status.APPROVED_BY_INSURANCE, permission=lambda i, u: u.has_perm('claims.can_process_broker'))
    def insurance_approve(self, user):
        self.log_status_change(
            user=user,
            from_status=self.status,
            to_status=Status.APPROVED_BY_INSURANCE,
            action='insurance_approve',
            reason='',
        )

    @transition(field=status, source=Status.SENT_TO_INSURANCE, target=Status.REJECTED_BY_INSURANCE, permission=lambda i, u: u.has_perm('claims.can_process_broker'))
    def insurance_reject(self, user, reason):
        self.rejection_reason = reason
        self.log_status_change(
            user=user,
            from_status=self.status,
            to_status=Status.REJECTED_BY_INSURANCE,
            action='insurance_reject',
            reason=reason,
        )

    # 7. السداد النهائي
    @transition(field=status, source=Status.APPROVED_BY_INSURANCE, target=Status.PAID, permission=lambda i, u: u.has_perm('claims.can_approve_payment'))
    def mark_as_paid(self, user, amount):
        self.approved_amount_sar = amount
        self.log_status_change(
            user=user,
            from_status=self.status,
            to_status=Status.PAID,
            action='mark_as_paid',
            reason='',
        )


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
    message = models.TextField(_("Comment Message"))
    
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
        permissions = [
            ("view_internal_comments", "Can view internal comments (Hidden from Member)"),
        ]       

    def __str__(self):
        return f"Comment by {self.author.username} on {self.claim.claim_reference}"


class ClaimStatusLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    claim = models.ForeignKey(
        Claim,
        on_delete=models.CASCADE,
        related_name='status_logs'
    )

    from_status = models.CharField(max_length=50)
    to_status = models.CharField(max_length=50)

    action = models.CharField(
        max_length=50,
        help_text="approve, reject, return, submit, pay..."
    )

    reason = models.TextField(blank=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
