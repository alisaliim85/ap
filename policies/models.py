import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _


# --- 0. قالب خطة التأمين (Insurance Plan Template Layer) ---

class InsurancePlan(models.Model):
    """
    منتج تأميني يُعرَّف مرة واحدة لكل وسيط + مزود تأمين.
    مثال: "بوبا الذهبي 2026" — يُستخدم كقالب لإنشاء وثائق متعددة.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    broker = models.ForeignKey(
        'brokers.Broker',
        on_delete=models.CASCADE,
        related_name='insurance_plans',
    )
    provider = models.ForeignKey(
        'providers.Provider',
        on_delete=models.PROTECT,
        related_name='plans',
    )
    name = models.CharField(_("Plan Name"), max_length=150)
    description = models.TextField(_("Description"), blank=True)
    is_active = models.BooleanField(_("Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('broker', 'provider', 'name')
        ordering = ['provider', 'name']
        permissions = [
            ("manage_insurance_plans", "Can create/edit insurance plan templates"),
        ]

    def __str__(self):
        return f"{self.name} ({self.provider})"


class PlanClass(models.Model):
    """
    فئة افتراضية داخل خطة التأمين (VIP, فئة أ, فئة ج ...).
    تحدد الشبكة الافتراضية والحد السنوي الافتراضي.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(
        InsurancePlan,
        on_delete=models.CASCADE,
        related_name='classes',
    )
    name = models.CharField(_("Class Name"), max_length=50)
    network = models.ForeignKey(
        'networks.Network',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='plan_classes',
        verbose_name=_("Default Network"),
    )
    annual_limit = models.DecimalField(
        _("Default Annual Limit"),
        max_digits=12,
        decimal_places=2,
    )
    order = models.PositiveSmallIntegerField(_("Display Order"), default=0)

    class Meta:
        unique_together = ('plan', 'name')
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.plan.name} — {self.name}"


class PlanClassBenefit(models.Model):
    """
    منفعة افتراضية داخل فئة الخطة.
    يمكن override هذه القيم في ClassBenefit على مستوى الوثيقة.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan_class = models.ForeignKey(
        PlanClass,
        on_delete=models.CASCADE,
        related_name='benefits',
    )
    benefit_type = models.ForeignKey(
        'BenefitType',
        on_delete=models.PROTECT,
        verbose_name=_("Benefit Type"),
    )
    limit_amount = models.DecimalField(
        _("Benefit Limit (SAR)"),
        max_digits=10,
        decimal_places=2,
        default=0,
    )
    deductible_percentage = models.IntegerField(
        _("Co-Pay %"),
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    description = models.TextField(_("Coverage Details"), blank=True)

    class Meta:
        unique_together = ('plan_class', 'benefit_type')

    def __str__(self):
        return f"{self.plan_class} — {self.benefit_type}: {self.limit_amount}"


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
    
    class Meta:
        permissions = [
            ("manage_benefit_types", "Can create/edit benefit types"),
        ]
    
    def __str__(self):
        return self.name_en

# --- 2. البوليصة (كما هي) ---
class Policy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='policies')
    
    # ربط الوثيقة بالأم (للشركات القابضة) - التعديل الجديد
    master_policy = models.ForeignKey(
        'self', 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True, 
        related_name='sub_policies',
        verbose_name=_("Master Policy (For Holding)")
    )
    provider = models.ForeignKey('providers.Provider', on_delete=models.CASCADE, related_name='issued_policies',null=True, blank=True)
    plan = models.ForeignKey(
        InsurancePlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='policies',
        verbose_name=_("Insurance Plan Template"),
    )
    policy_number = models.CharField(_("Policy Number"), max_length=100)
    start_date = models.DateField(_("Start Date"))
    end_date = models.DateField(_("End Date"))
    contract_file = models.FileField(upload_to='policies/contracts/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('client', 'policy_number')
        permissions = [
            ("manage_policy_structure", "Can create/edit policies and classes"),
            ("view_policy_details", "Can view policy coverage details"),
        ]
    # 3. المنطق الذكي لاسترجاع المزود
    @property
    def effective_provider(self):
        """
        استرجاع المزود الفعلي.
        إذا كانت وثيقة تابعة، نعود لمزود الوثيقة الأم.
        """
        if self.master_policy:
            return self.master_policy.provider
        return self.provider

    # 4. التحقق والملء التلقائي قبل الحفظ
    def clean(self):
        # التحقق: لا يمكن أن يكون كلاهما فارغاً
        if not self.master_policy and not self.provider:
            raise ValidationError(_("Either a Master Policy or an Insurance Provider must be specified."))
        
        # التحقق: إذا كانت تابعة، يجب أن لا نحدد مزوداً مختلفاً (اختياري، أو نفرضه)
        if self.master_policy and self.provider:
            if self.master_policy.provider != self.provider:
                raise ValidationError(_("Subsidiary policy must have the same provider as the master policy."))

    def save(self, *args, **kwargs):
        # قبل الحفظ، إذا كانت وثيقة تابعة، يمكننا نسخ المزود من الأم لسهولة البحث (اختياري)
        # أو نتركه فارغاً ونعتمد على effective_provider
        
        # الخيار الأفضل للأداء (Denormalization for Performance):
        # نقوم بنسخ المزود للحقل لكي تعمل استعلامات الفلترة السريعة (Filtering) دون Join معقد
        if self.master_policy:
            self.provider = self.master_policy.provider
            
        super().save(*args, **kwargs)

    def __str__(self):
        type_str = "Sub-Policy" if self.master_policy else "Master"
        return f"{self.policy_number} - {self.client.name_en} ({type_str})"

    # --- دوال المنطق الذكي (Business Logic) ---

    @property
    def is_subsidiary(self):
        """هل هذه وثيقة تابعة لشركة قابضة؟"""
        return self.master_policy is not None

    @property
    def effective_classes(self):
        """
        إرجاع الفئات المتاحة لهذه الوثيقة.
        - إذا كانت وثيقة أم: تُرجع فئاتها الخاصة.
        - إذا كانت وثيقة تابعة: ترث وتُرجع فئات الوثيقة الأم.
        """
        if self.is_subsidiary:
            return self.master_policy.classes.all()
        return self.classes.all()
# --- 3. الفئة (تم التعديل لإزالة الحقول الثابتة) ---
class PolicyClass(models.Model):
    """
    الفئة تحدد الشبكة والحد العام، ولكن تفاصيل المنافع تكون في جدول منفصل
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy = models.ForeignKey(Policy, on_delete=models.CASCADE, related_name='classes')
    
    plan_class = models.ForeignKey(
        PlanClass,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='policy_classes',
        verbose_name=_("Plan Class Template"),
    )

    # ربط الفئة بالشبكة الطبية
    network = models.ForeignKey(
        'networks.Network',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='policy_classes',
        verbose_name=_("Linked Network")
    )

    name = models.CharField(_("Class Name"), max_length=50)  # VIP, Class A

    # تخصيص مستشفيات الفئة على مستوى الوثيقة (يتجاوز شبكة الخطة)
    excluded_providers = models.ManyToManyField(
        'networks.ServiceProvider',
        blank=True,
        related_name='excluded_in_classes',
        verbose_name=_("Excluded Hospitals"),
        help_text=_("Hospitals to exclude from this class's effective network."),
    )
    extra_providers = models.ManyToManyField(
        'networks.ServiceProvider',
        blank=True,
        related_name='added_in_classes',
        verbose_name=_("Extra Hospitals"),
        help_text=_("Additional hospitals beyond the assigned network."),
    )

    # الحد السنوي — nullable: null يعني يرث من plan_class
    annual_limit = models.DecimalField(
        _("General Annual Limit"),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Leave blank to inherit from plan class template."),
    )

    class Meta:
        unique_together = ('policy', 'name')

    # --- خصائص الوراثة (Inheritance Properties) ---

    @property
    def effective_network(self):
        """الشبكة الفعلية: override الوثيقة أولاً، ثم قالب الخطة."""
        if self.network_id:
            return self.network
        if self.plan_class_id:
            return self.plan_class.network
        return None

    def get_effective_providers(self):
        """
        يُرجع QuerySet بالمستشفيات الفعلية لهذه الفئة:
        - مستشفيات الشبكة الفعلية
        - ناقصاً المستشفيات المستبعدة (excluded_providers)
        - زائداً المستشفيات الإضافية (extra_providers)
        """
        from networks.models import ServiceProvider
        network = self.effective_network
        if network:
            base_ids = set(network.hospitals.values_list('id', flat=True))
        else:
            base_ids = set()

        excluded_ids = set(self.excluded_providers.values_list('id', flat=True))
        extra_ids = set(self.extra_providers.values_list('id', flat=True))

        final_ids = (base_ids - excluded_ids) | extra_ids
        if not final_ids:
            return ServiceProvider.objects.none()
        return ServiceProvider.objects.filter(id__in=final_ids).order_by('name_ar')

    @property
    def effective_annual_limit(self):
        """الحد السنوي الفعلي: override الوثيقة أولاً، ثم قالب الخطة."""
        if self.annual_limit is not None:
            return self.annual_limit
        if self.plan_class_id:
            return self.plan_class.annual_limit
        return None

    def get_effective_benefits(self):
        """
        يُرجع قائمة المنافع الفعلية مع تفادي N+1.
        الأولوية: ClassBenefit (override) ثم PlanClassBenefit (افتراضي).
        المنافع ذات is_excluded=True تُحذف من النتيجة.

        يجب استدعاء هذه الدالة بعد prefetch_related كالتالي:
            PolicyClass.objects.prefetch_related(
                'benefits__benefit_type',
                'plan_class__benefits__benefit_type',
            )
        """
        overrides = {b.benefit_type_id: b for b in self.benefits.all()}

        if not self.plan_class_id:
            # لا خطة — فقط أعد المنافع المباشرة غير المستبعدة
            return [b for b in self.benefits.all() if not b.is_excluded]

        result = []
        seen_ids = set()

        for pb in self.plan_class.benefits.all():
            seen_ids.add(pb.benefit_type_id)
            if pb.benefit_type_id in overrides:
                override = overrides[pb.benefit_type_id]
                if not override.is_excluded:
                    result.append(override)  # override بقيم مختلفة
                # إذا is_excluded=True — لا نضيف المنفعة (مستبعدة)
            else:
                result.append(pb)  # موروثة من الخطة بدون تعديل

        # منافع override مباشرة غير موجودة في قالب الخطة
        for b in self.benefits.all():
            if b.benefit_type_id not in seen_ids and not b.is_excluded:
                result.append(b)

        return result

    def clean(self):
        # التحقق: الشبكة الفعلية يجب أن تنتمي لنفس مزود تأمين الوثيقة
        effective_net = self.effective_network
        if effective_net and self.policy_id:
            effective_provider = self.policy.effective_provider
            if effective_provider and effective_net.provider_id != effective_provider.pk:
                raise ValidationError(
                    _("The selected network does not belong to the policy's insurance provider. "
                      "Expected provider: %(expected)s, got: %(got)s.") % {
                        'expected': effective_provider,
                        'got': effective_net.provider,
                    }
                )

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
    # استبعاد المنفعة الموروثة من الخطة (Override بالاستبعاد)
    is_excluded = models.BooleanField(
        _("Excluded"),
        default=False,
        help_text=_("If checked, this benefit is excluded from coverage even if inherited from the plan."),
    )
    class Meta:
        unique_together = ('policy_class', 'benefit_type') # لا تكرر نفس المنفعة لنفس الفئة
        verbose_name = _("Class Benefit Detail")

    def __str__(self):
        return f"{self.policy_class.name} - {self.benefit_type.name_en}: {self.limit_amount}"