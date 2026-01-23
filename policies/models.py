import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _

# --- 1. أنواع المنافع (Master Data) ---
class BenefitType(models.Model):
    """
    تعريف أنواع المنافع بشكل عام للنظام
    مثال: Dental, Optical, Maternity, In-Patient, Out-Patient
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name_ar = models.CharField(_("Arabic Name"), max_length=100) # أسنان
    name_en = models.CharField(_("English Name"), max_length=100) # Dental
    icon = models.CharField(max_length=50, blank=True, help_text="FontAwesome icon name (e.g., fa-tooth)")
    
    def __str__(self):
        return self.name_en

# --- 2. البوليصة (كما هي) ---
class Policy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='policies')
    provider = models.ForeignKey('providers.Provider', on_delete=models.CASCADE, related_name='issued_policies')
    policy_number = models.CharField(_("Policy Number"), max_length=100)
    start_date = models.DateField(_("Start Date"))
    end_date = models.DateField(_("End Date"))
    contract_file = models.FileField(upload_to='policies/contracts/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('client', 'policy_number')

    def __str__(self):
        return f"{self.policy_number} - {self.client.name_en}"

# --- 3. الفئة (تم التعديل لإزالة الحقول الثابتة) ---
class PolicyClass(models.Model):
    """
    الفئة تحدد الشبكة والحد العام، ولكن تفاصيل المنافع تكون في جدول منفصل
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy = models.ForeignKey(Policy, on_delete=models.CASCADE, related_name='classes')
    
    # ربط الفئة بالشبكة الطبية
    network = models.ForeignKey(
        'networks.Network',
        on_delete=models.SET_NULL,
        null=True,
        related_name='policy_classes',
        verbose_name=_("Linked Network")
    )
    
    name = models.CharField(_("Class Name"), max_length=50) # VIP, Class A
    
    # الحد السنوي العام للفئة (General Annual Limit)
    annual_limit = models.DecimalField(_("General Annual Limit"), max_digits=12, decimal_places=2)
    
    class Meta:
        unique_together = ('policy', 'name')

    def __str__(self):
        return f"{self.name} - {self.policy.policy_number}"

# --- 4. تفاصيل المنافع لكل فئة (الجدول الجديد الهام جداً) ---
class ClassBenefit(models.Model):
    """
    هنا يتم تحديد سقف التغطية لكل منفعة لكل فئة
    مثال:
    - VIP Class -> Dental -> Limit: 5000 SAR
    - Class A -> Dental -> Limit: 3000 SAR
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    policy_class = models.ForeignKey(
        PolicyClass, 
        on_delete=models.CASCADE, 
        related_name='benefits'
    )
    
    benefit_type = models.ForeignKey(
        BenefitType, 
        on_delete=models.PROTECT,
        verbose_name=_("Benefit Type")
    )
    
    # الحد المالي لهذه المنفعة (sub-limit)
    limit_amount = models.DecimalField(
        _("Benefit Limit (SAR)"), 
        max_digits=10, 
        decimal_places=2,
        default=0,
        help_text=_("E.g., 5000 for Dental")
    )
    
    # نسبة التحمل الخاصة بهذه المنفعة (قد تختلف عن التحمل العام)
    deductible_percentage = models.IntegerField(
        _("Co-Pay %"), 
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Percentage user pays specific to this benefit")
    )
    
    description = models.TextField(_("Coverage Details"), blank=True)

    class Meta:
        unique_together = ('policy_class', 'benefit_type') # لا تكرر نفس المنفعة لنفس الفئة
        verbose_name = _("Class Benefit Detail")

    def __str__(self):
        return f"{self.policy_class.name} - {self.benefit_type.name_en}: {self.limit_amount}"