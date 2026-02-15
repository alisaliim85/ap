import uuid
import datetime
from django.db import models
from django.utils.translation import gettext_lazy as _


# --- 1. الثوابت والأمراض ---
class ChronicDisease(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name_ar = models.CharField(_("Disease Name (AR)"), max_length=100)
    name_en = models.CharField(_("Disease Name (EN)"), max_length=100)
    class Meta:
         permissions = [
            ("manage_disease_list", "Can manage disease list configuration"),
        ]
    
    def __str__(self):
        return self.name_en

# --- 2. طلب الانضمام (نفس السابق) ---
class ChronicRequest(models.Model):
    class Status(models.TextChoices):
        NEW = 'NEW', _('New Request')
        UNDER_BROKER_REVIEW = 'UNDER_BROKER_REVIEW', _('Under Broker Review')
        ASSIGNED_TO_PARTNER = 'ASSIGNED_TO_PARTNER', _('Assigned to Partner')
        REJECTED = 'REJECTED', _('Rejected')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey('members.Member', on_delete=models.CASCADE, related_name='chronic_requests')
    disease = models.ForeignKey(ChronicDisease, on_delete=models.PROTECT)
    medical_report = models.FileField(upload_to='chronic/requests/%Y/%m/')
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.NEW)
    
    assigned_partner = models.ForeignKey(
        'partners.Partner',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        limit_choices_to={'partner_type': 'CHRONIC_CENTER'},
        related_name='assigned_chronic_requests'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        permissions = [
            ("manage_chronic_requests", "Can create/edit chronic requests"),
            ("approve_request", "Can approve/reject chronic requests"),
            ("assign_partner", "Can assign partner to chronic requests"),
        ]

# --- 3. ملف الحالة وإعدادات الجدولة الآلية ---
class ChronicCase(models.Model):
    """
    هنا نضبط "إيقاع" الزيارات المنزلية
    """
    class VisitFrequency(models.IntegerChoices):
        WEEKLY = 7, _('Weekly')
        BI_WEEKLY = 14, _('Every 2 Weeks')
        MONTHLY = 30, _('Monthly')
        QUARTERLY = 90, _('Every 3 Months')

    class CaseStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Active Care')
        SUSPENDED = 'SUSPENDED', _('Suspended')
        COMPLETED = 'COMPLETED', _('Completed')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.OneToOneField(ChronicRequest, on_delete=models.CASCADE, related_name='case_file')
    managing_partner = models.ForeignKey('partners.Partner', on_delete=models.PROTECT)
    
    # إعدادات الجدولة الآلية
    start_date = models.DateField(_("Start Date"))
    frequency_days = models.IntegerField(
        _("Visit Frequency"), 
        choices=VisitFrequency.choices,
        default=VisitFrequency.MONTHLY
    )
    
    # متى الزيارة القادمة المتوقعة؟ (النظام يحدث هذا الحقل)
    next_visit_due = models.DateField(_("Next Visit Due Date"), null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=CaseStatus.choices, default=CaseStatus.ACTIVE)
    
    # الموقع الجغرافي للمنزل (يتم جلبه من عنوان المريض)
    home_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    home_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    class Meta: 
        permissions = [
            ("manage_chronic_cases", "Can create/edit chronic cases"),
            ("suspend_case", "Can suspend or terminate chronic cases"),

        ]

    def __str__(self):
        return f"Home Care: {self.request.member.full_name}"


# --- 4. الزيارات المنزلية (Home Visits) ---
class HomeVisit(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = 'SCHEDULED', _('Scheduled (Auto)')
        CONFIRMED = 'CONFIRMED', _('Confirmed with Patient')
        ON_THE_WAY = 'ON_THE_WAY', _('Doctor on the Way')
        IN_PROGRESS = 'IN_PROGRESS', _('Visit In Progress')
        COMPLETED = 'COMPLETED', _('Visit Completed')
        CANCELLED = 'CANCELLED', _('Cancelled')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(ChronicCase, on_delete=models.CASCADE, related_name='visits')
    
    # الطبيب المعالج (User linked to Partner)
    doctor = models.ForeignKey(
        'accounts.User', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        limit_choices_to={'role': 'CHRONIC_STAFF'},
        verbose_name=_("Assigned Doctor")
    )
    
    scheduled_date = models.DateTimeField(_("Scheduled Date"))
    actual_visit_start = models.DateTimeField(null=True, blank=True)
    actual_visit_end = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    
    # تقرير الزيارة (مشفر)
    # ملاحظة: الطبيب يكتب هنا التشخيص العام
    doctor_notes = models.TextField(_("Doctor Clinical Notes"), blank=True)
    vital_pressure = models.CharField(max_length=20, blank=True)
    vital_sugar = models.CharField(max_length=20, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['scheduled_date']
        permissions = [
            ("manage_home_visits", "Can create/edit home visits"),
            ("process_visit", "Can start/complete home visits"),
            ("view_sensitive_medical_data", "Can view encrypted doctor notes"),
        ]   

    def __str__(self):
        return f"Visit: {self.case.request.member.full_name} on {self.scheduled_date.date()}"

    def save(self, *args, **kwargs):
        # المنطق السحري: إذا اكتملت الزيارة، قم بجدولة الزيارة القادمة
        # (هذا تبسيط، يفضل وضع هذا المنطق في Views أو Signals لاحقاً)
        super().save(*args, **kwargs)


# --- 5. الإجراءات الطبية أثناء الزيارة ---

class VisitPrescription(models.Model):
    """
    الأدوية التي قررها الطبيب أثناء الزيارة
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.ForeignKey(HomeVisit, on_delete=models.CASCADE, related_name='prescriptions')
    
    medication_name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100) # e.g. 500mg twice a day
    quantity = models.IntegerField(default=1)
    
    instructions = models.TextField(_("Instructions"), blank=True)
    
    is_dispensed = models.BooleanField(default=False)
    class Meta:
        default_permissions = ('add', 'change', 'delete', 'view')

class VisitLabRequest(models.Model):
    """
    التحاليل المطلوبة (Lab Tests)
    """
    class ResultStatus(models.TextChoices):
        PENDING = 'PENDING', _('Sample Taken / Pending Result')
        UPLOADED = 'UPLOADED', _('Result Uploaded')
        NOTIFIED = 'NOTIFIED', _('Patient Notified')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.ForeignKey(HomeVisit, on_delete=models.CASCADE, related_name='lab_requests')
    
    test_name = models.CharField(_("Test Name"), max_length=200) # e.g. HbA1c, CBC
    
    status = models.CharField(max_length=20, choices=ResultStatus.choices, default=ResultStatus.PENDING)
    
    # ملف النتيجة (يجب حمايته في الـ Views)
    result_file = models.FileField(upload_to='chronic/labs/%Y/%m/', null=True, blank=True)
    
    # قراءة النتيجة نصياً (مشفرة)
    result_summary = models.TextField(_("Result Summary"), blank=True)
    
    # توقيت ظهور النتيجة
    result_date = models.DateTimeField(null=True, blank=True)
    
    # هل تم إبلاغ المريض؟
    patient_notified = models.BooleanField(default=False)
    notification_notes = models.TextField(blank=True, help_text="e.g. Called patient at 5 PM")
    class Meta:
        permissions = [
            ("upload_lab_result", "Can upload lab test results"),
        ]
    def __str__(self):
        return f"{self.test_name} ({self.get_status_display()})"