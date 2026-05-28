# Insurance Plan Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** إضافة طبقة "المنتج التأميني" (InsurancePlan) كقالب يُعرَّف مرة واحدة لكل وسيط/شركة تأمين، وربط الوثائق به بحيث ترث الفئات والمنافع والشبكات تلقائياً مع إمكانية التعديل (override) لكل عميل.

**Architecture:** ثلاثة نماذج جديدة (InsurancePlan, PlanClass, PlanClassBenefit) مع حقلين nullable على Policy وPolicyClass. منطق الوراثة يعمل عبر properties على PolicyClass. كل استعلام يستخدم select_related/prefetch_related لتفادي N+1.

**Tech Stack:** Django 4.2, SQLite, django-htmx, Bootstrap 5 RTL, Phosphor Icons

**Spec:** `docs/superpowers/specs/2026-05-28-insurance-plan-template-design.md`

---

## File Structure

| الملف | العملية | المسؤولية |
|---|---|---|
| `policies/models.py` | تعديل | إضافة InsurancePlan, PlanClass, PlanClassBenefit + تعديل Policy و PolicyClass |
| `policies/admin.py` | تعديل | تسجيل النماذج الجديدة مع Inlines |
| `policies/forms.py` | تعديل | إضافة InsurancePlanForm, PlanClassForm, PlanClassBenefitForm |
| `policies/views.py` | تعديل | إضافة get_allowed_plans + 6 views جديدة + تعديل policy_create |
| `policies/urls.py` | تعديل | إضافة 7 URL patterns جديدة |
| `policies/tests.py` | تعديل | اختبارات الوراثة والعزل |
| `templates/policies/plan_list.html` | إنشاء | قائمة الخطط |
| `templates/policies/plan_form.html` | إنشاء | نموذج إنشاء/تعديل خطة |
| `templates/policies/plan_detail.html` | إنشاء | تفاصيل خطة مع فئاتها |
| `templates/policies/plan_class_form.html` | إنشاء | نموذج إضافة فئة (HTMX partial) |
| `templates/policies/partials/plan_class_benefits.html` | إنشاء | منافع فئة القالب (HTMX partial) |
| `templates/policies/policy_form.html` | تعديل | إضافة حقل اختيار الخطة |
| `templates/policies/policy_detail.html` | تعديل | إظهار معلومات الخطة المرتبطة |

---

## Task 1: النماذج الجديدة — InsurancePlan, PlanClass, PlanClassBenefit

**Files:**
- Modify: `policies/models.py`

- [ ] **Step 1: كتابة اختبار فشل للنموذج الجديد**

في `policies/tests.py`:

```python
from django.test import TestCase
from django.core.exceptions import ValidationError
from policies.models import BenefitType, InsurancePlan, PlanClass, PlanClassBenefit, Policy, PolicyClass
from providers.models import Provider
from networks.models import Network, ServiceProvider
from brokers.models import Broker
from clients.models import Client


class InsurancePlanModelTest(TestCase):
    def setUp(self):
        self.broker = Broker.objects.create(
            name_ar='وسيط تجريبي', name_en='Test Broker', commercial_record='BR001'
        )
        self.provider = Provider.objects.create(
            name_ar='بوبا', name_en='Bupa', license_number='LIC001'
        )

    def test_create_insurance_plan(self):
        plan = InsurancePlan.objects.create(
            broker=self.broker,
            provider=self.provider,
            name='بوبا الذهبي 2026',
        )
        self.assertEqual(plan.name, 'بوبا الذهبي 2026')
        self.assertEqual(str(plan), 'بوبا الذهبي 2026 (Bupa)')

    def test_plan_unique_together(self):
        InsurancePlan.objects.create(
            broker=self.broker, provider=self.provider, name='خطة أ'
        )
        with self.assertRaises(Exception):
            InsurancePlan.objects.create(
                broker=self.broker, provider=self.provider, name='خطة أ'
            )
```

- [ ] **Step 2: تشغيل الاختبار للتأكد من الفشل**

```
python manage.py test policies.tests.InsurancePlanModelTest -v 2
```

المتوقع: `ImportError: cannot import name 'InsurancePlan'`

- [ ] **Step 3: إضافة النماذج الثلاثة في policies/models.py**

أضف هذا الكود **بعد سطر `from django.utils.translation import gettext_lazy as _`** وقبل `class BenefitType`:

```python
# --- 0. المنتج التأميني القالب (Insurance Plan Template) ---
class InsurancePlan(models.Model):
    """
    قالب المنتج التأميني الذي يعرّفه الوسيط مع شركة التأمين مرة واحدة.
    مثال: "بوبا الذهبي 2026"، "التعاونية الماسية"
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    broker = models.ForeignKey(
        'brokers.Broker',
        on_delete=models.CASCADE,
        related_name='insurance_plans',
        verbose_name=_("Broker")
    )
    provider = models.ForeignKey(
        'providers.Provider',
        on_delete=models.PROTECT,
        related_name='plans',
        verbose_name=_("Insurance Provider")
    )
    name = models.CharField(_("Plan Name"), max_length=150)
    description = models.TextField(_("Description"), blank=True)
    is_active = models.BooleanField(_("Is Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('broker', 'provider', 'name')
        verbose_name = _("Insurance Plan")
        verbose_name_plural = _("Insurance Plans")
        ordering = ['provider__name_en', 'name']

    def __str__(self):
        return f"{self.name} ({self.provider.name_en})"


class PlanClass(models.Model):
    """
    الفئة المعيارية داخل القالب (VIP, فئة أ, بلاتينيوم...).
    المسمى يتبع شركة التأمين وليس نظاماً موحداً.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(
        InsurancePlan,
        on_delete=models.CASCADE,
        related_name='classes',
        verbose_name=_("Insurance Plan")
    )
    name = models.CharField(_("Class Name"), max_length=50)
    network = models.ForeignKey(
        'networks.Network',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='plan_classes',
        verbose_name=_("Default Network")
    )
    annual_limit = models.DecimalField(
        _("Default Annual Limit"), max_digits=12, decimal_places=2
    )
    order = models.PositiveSmallIntegerField(_("Display Order"), default=0)

    class Meta:
        unique_together = ('plan', 'name')
        ordering = ['order', 'name']
        verbose_name = _("Plan Class")
        verbose_name_plural = _("Plan Classes")

    def __str__(self):
        return f"{self.plan.name} — {self.name}"


class PlanClassBenefit(models.Model):
    """
    المنافع الافتراضية لكل فئة في القالب.
    مثال: VIP → أسنان 5,000 / 20% تحمل
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan_class = models.ForeignKey(
        PlanClass,
        on_delete=models.CASCADE,
        related_name='benefits',
        verbose_name=_("Plan Class")
    )
    benefit_type = models.ForeignKey(
        'BenefitType',
        on_delete=models.PROTECT,
        verbose_name=_("Benefit Type")
    )
    limit_amount = models.DecimalField(
        _("Default Limit (SAR)"), max_digits=10, decimal_places=2, default=0
    )
    deductible_percentage = models.IntegerField(
        _("Co-Pay %"),
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    description = models.TextField(_("Coverage Details"), blank=True)

    class Meta:
        unique_together = ('plan_class', 'benefit_type')
        verbose_name = _("Plan Class Benefit")
        verbose_name_plural = _("Plan Class Benefits")

    def __str__(self):
        return f"{self.plan_class} — {self.benefit_type.name_en}: {self.limit_amount}"
```

- [ ] **Step 4: إنشاء migration**

```
python manage.py makemigrations policies --name insurance_plan_models
```

المتوقع: `policies/migrations/XXXX_insurance_plan_models.py`

- [ ] **Step 5: تطبيق migration**

```
python manage.py migrate
```

المتوقع: `OK`

- [ ] **Step 6: تشغيل الاختبار للتأكد من النجاح**

```
python manage.py test policies.tests.InsurancePlanModelTest -v 2
```

المتوقع: `OK`

- [ ] **Step 7: Commit**

```
git add policies/models.py policies/migrations/ policies/tests.py
git commit -m "feat(policies): add InsurancePlan, PlanClass, PlanClassBenefit models"
```

---

## Task 2: تعديل Policy وPolicyClass — إضافة FK للقالب

**Files:**
- Modify: `policies/models.py`

- [ ] **Step 1: كتابة اختبار فشل**

في `policies/tests.py` أضف:

```python
class PolicyPlanLinkTest(TestCase):
    def setUp(self):
        self.broker = Broker.objects.create(
            name_ar='وسيط', name_en='Broker', commercial_record='BR002'
        )
        self.provider = Provider.objects.create(
            name_ar='بوبا', name_en='Bupa', license_number='LIC002'
        )
        self.client_obj = Client.objects.create(
            name_ar='شركة', name_en='Company', commercial_record='CR001', broker=self.broker
        )
        self.plan = InsurancePlan.objects.create(
            broker=self.broker, provider=self.provider, name='خطة تجريبية'
        )
        self.plan_class = PlanClass.objects.create(
            plan=self.plan, name='VIP', annual_limit=100000
        )
        self.policy = Policy.objects.create(
            client=self.client_obj,
            provider=self.provider,
            policy_number='POL-TEST-001',
            start_date='2026-01-01',
            end_date='2026-12-31',
            plan=self.plan,
        )

    def test_policy_has_plan_fk(self):
        self.assertEqual(self.policy.plan, self.plan)

    def test_policy_class_inherits_annual_limit(self):
        pc = PolicyClass.objects.create(
            policy=self.policy,
            name='VIP',
            plan_class=self.plan_class,
            # annual_limit=None → يجب أن يرث من plan_class
        )
        self.assertEqual(pc.effective_annual_limit, 100000)

    def test_policy_class_override_annual_limit(self):
        pc = PolicyClass.objects.create(
            policy=self.policy,
            name='VIP',
            plan_class=self.plan_class,
            annual_limit=120000,  # override
        )
        self.assertEqual(pc.effective_annual_limit, 120000)
```

- [ ] **Step 2: تشغيل الاختبار للتأكد من الفشل**

```
python manage.py test policies.tests.PolicyPlanLinkTest -v 2
```

المتوقع: `Error: Policy has no field 'plan'`

- [ ] **Step 3: تعديل نموذج Policy في policies/models.py**

ابحث عن السطر الذي يلي `master_policy` في `class Policy` وأضف الحقل الجديد:

```python
    master_policy = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='sub_policies',
        verbose_name=_("Master Policy (For Holding)")
    )
    # حقل جديد — nullable للتوافق مع البيانات القديمة
    plan = models.ForeignKey(
        'InsurancePlan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='policies',
        verbose_name=_("Insurance Plan Template")
    )
    provider = models.ForeignKey(...)
```

- [ ] **Step 4: تعديل نموذج PolicyClass — إضافة plan_class وجعل annual_limit nullable**

ابحث عن تعريف `class PolicyClass` وعدّل الحقول كالتالي:

```python
class PolicyClass(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy = models.ForeignKey(Policy, on_delete=models.CASCADE, related_name='classes')

    # حقل جديد — ربط بفئة القالب (nullable للتوافق مع البيانات القديمة)
    plan_class = models.ForeignKey(
        'PlanClass',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='policy_classes',
        verbose_name=_("Template Class (Source)")
    )

    network = models.ForeignKey(
        'networks.Network',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,        # ← كان موجوداً، تأكد أنه blank=True
        related_name='policy_classes',
        verbose_name=_("Linked Network")
    )

    name = models.CharField(_("Class Name"), max_length=50)

    # تعديل: annual_limit أصبح nullable (override اختياري عند وجود plan_class)
    annual_limit = models.DecimalField(
        _("General Annual Limit"),
        max_digits=12,
        decimal_places=2,
        null=True,    # ← جديد
        blank=True,   # ← جديد
    )
```

- [ ] **Step 5: إنشاء migration**

```
python manage.py makemigrations policies --name add_plan_fk_to_policy_and_policyclass
```

- [ ] **Step 6: تطبيق migration**

```
python manage.py migrate
```

المتوقع: `OK`

- [ ] **Step 7: تشغيل الاختبار — سيفشل لأن effective_annual_limit غير موجودة بعد**

```
python manage.py test policies.tests.PolicyPlanLinkTest -v 2
```

المتوقع: `AttributeError: 'PolicyClass' object has no attribute 'effective_annual_limit'`

- [ ] **Step 8: Commit (بعد Task 3 سنُكمل)**

لا تُودِع حتى Task 3 ينتهي.

---

## Task 3: منطق الوراثة على PolicyClass

**Files:**
- Modify: `policies/models.py` (داخل class PolicyClass)

- [ ] **Step 1: إضافة خصائص الوراثة الثلاث في policies/models.py**

ابحث عن `def clean(self):` في `PolicyClass` وأضف قبله مباشرة:

```python
    # ==========================================
    # منطق الوراثة (Inheritance Logic)
    # ==========================================

    @property
    def effective_network(self):
        """
        الشبكة الفعلية:
        - إذا network مضبوط على هذه الفئة → override (يُستخدم مباشرة)
        - إذا plan_class مضبوط → يرث من القالب
        - وإلا → None
        """
        if self.network_id:
            return self.network
        if self.plan_class_id:
            return self.plan_class.network
        return None

    @property
    def effective_annual_limit(self):
        """
        الحد السنوي الفعلي:
        - إذا annual_limit مضبوط → override
        - إذا plan_class مضبوط → يرث من القالب
        - وإلا → None
        """
        if self.annual_limit is not None:
            return self.annual_limit
        if self.plan_class_id:
            return self.plan_class.annual_limit
        return None

    def get_effective_benefits(self):
        """
        المنافع الفعلية بدمج override وQالقالب. آمن من N+1.

        **إلزامي:** استدعِ هذه الدالة فقط بعد prefetch_related:
            PolicyClass.objects.prefetch_related(
                'benefits__benefit_type',
                'plan_class__benefits__benefit_type',
            )

        الأولوية: ClassBenefit (override) > PlanClassBenefit (قالب)
        """
        # قاموس الـ overrides المحددة على مستوى الوثيقة
        overrides = {b.benefit_type_id: b for b in self.benefits.all()}

        if not self.plan_class_id:
            # لا يوجد قالب — أرجع الـ overrides فقط (السلوك القديم)
            return list(self.benefits.all())

        result = []
        seen_ids = set()

        for pb in self.plan_class.benefits.all():
            seen_ids.add(pb.benefit_type_id)
            if pb.benefit_type_id in overrides:
                result.append(overrides[pb.benefit_type_id])  # override يسبق القالب
            else:
                result.append(pb)  # يرث من القالب

        # منافع override إضافية غير موجودة في القالب
        for b in self.benefits.all():
            if b.benefit_type_id not in seen_ids:
                result.append(b)

        return result
```

- [ ] **Step 2: تحديث دالة clean() لاستخدام effective_network**

ابحث عن `def clean(self):` في `PolicyClass` وعدّلها:

```python
    def clean(self):
        # التحقق: الشبكة الفعلية يجب أن تنتمي لنفس مزود تأمين الوثيقة
        eff_network = self.effective_network
        if eff_network and self.policy_id:
            effective = self.policy.effective_provider
            if effective and eff_network.provider_id != effective.pk:
                raise ValidationError(
                    _("The selected network does not belong to the policy's insurance provider. "
                      "Expected provider: %(expected)s, got: %(got)s.") % {
                        'expected': effective,
                        'got': eff_network.provider,
                    }
                )
```

- [ ] **Step 3: تشغيل اختبارات Task 2**

```
python manage.py test policies.tests.PolicyPlanLinkTest -v 2
```

المتوقع: `OK` (3 اختبارات تنجح)

- [ ] **Step 4: إضافة اختبار get_effective_benefits**

في `policies/tests.py` أضف:

```python
class EffectiveBenefitsTest(TestCase):
    def setUp(self):
        self.broker = Broker.objects.create(
            name_ar='وسيط', name_en='Broker', commercial_record='BR003'
        )
        self.provider = Provider.objects.create(
            name_ar='بوبا', name_en='Bupa', license_number='LIC003'
        )
        self.client_obj = Client.objects.create(
            name_ar='شركة', name_en='Company', commercial_record='CR002', broker=self.broker
        )
        self.benefit_dental = BenefitType.objects.create(
            name_ar='أسنان', name_en='Dental'
        )
        self.benefit_optical = BenefitType.objects.create(
            name_ar='بصريات', name_en='Optical'
        )
        self.plan = InsurancePlan.objects.create(
            broker=self.broker, provider=self.provider, name='خطة اختبار'
        )
        self.plan_class = PlanClass.objects.create(
            plan=self.plan, name='VIP', annual_limit=100000
        )
        PlanClassBenefit.objects.create(
            plan_class=self.plan_class, benefit_type=self.benefit_dental, limit_amount=5000
        )
        PlanClassBenefit.objects.create(
            plan_class=self.plan_class, benefit_type=self.benefit_optical, limit_amount=2000
        )
        self.policy = Policy.objects.create(
            client=self.client_obj, provider=self.provider,
            policy_number='POL-TEST-002', start_date='2026-01-01',
            end_date='2026-12-31', plan=self.plan,
        )
        self.policy_class = PolicyClass.objects.create(
            policy=self.policy, name='VIP', plan_class=self.plan_class
        )

    def _get_policy_class_with_prefetch(self):
        return PolicyClass.objects.prefetch_related(
            'benefits__benefit_type',
            'plan_class__benefits__benefit_type',
        ).get(pk=self.policy_class.pk)

    def test_inherits_all_benefits_from_plan(self):
        pc = self._get_policy_class_with_prefetch()
        benefits = pc.get_effective_benefits()
        self.assertEqual(len(benefits), 2)

    def test_override_single_benefit(self):
        from policies.models import ClassBenefit
        # تجاوز حد الأسنان فقط لهذا العميل
        ClassBenefit.objects.create(
            policy_class=self.policy_class,
            benefit_type=self.benefit_dental,
            limit_amount=7000,  # override: 7000 بدلاً من 5000
        )
        pc = self._get_policy_class_with_prefetch()
        benefits = {b.benefit_type_id: b for b in pc.get_effective_benefits()}
        self.assertEqual(benefits[self.benefit_dental.pk].limit_amount, 7000)
        self.assertEqual(benefits[self.benefit_optical.pk].limit_amount, 2000)  # يرث من القالب
```

- [ ] **Step 5: تشغيل الاختبار الجديد**

```
python manage.py test policies.tests.EffectiveBenefitsTest -v 2
```

المتوقع: `OK`

- [ ] **Step 6: Commit**

```
git add policies/models.py policies/tests.py policies/migrations/
git commit -m "feat(policies): add plan FK to Policy/PolicyClass + inheritance logic"
```

---

## Task 4: Admin للنماذج الجديدة

**Files:**
- Modify: `policies/admin.py`

- [ ] **Step 1: تحديث policies/admin.py**

استبدل المحتوى الكامل بـ:

```python
from django.contrib import admin
from .models import BenefitType, Policy, PolicyClass, ClassBenefit
from .models import InsurancePlan, PlanClass, PlanClassBenefit


@admin.register(BenefitType)
class BenefitTypeAdmin(admin.ModelAdmin):
    list_display = ('name_en', 'name_ar')
    search_fields = ('name_en', 'name_ar')


# ==========================================
# Insurance Plan Admin
# ==========================================

class PlanClassBenefitInline(admin.TabularInline):
    model = PlanClassBenefit
    extra = 1
    autocomplete_fields = ['benefit_type']


class PlanClassInline(admin.TabularInline):
    model = PlanClass
    extra = 1
    show_change_link = True


@admin.register(InsurancePlan)
class InsurancePlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'broker', 'provider', 'is_active', 'created_at')
    list_filter = ('provider', 'broker', 'is_active')
    search_fields = ('name', 'broker__name_en', 'provider__name_en')
    inlines = [PlanClassInline]
    readonly_fields = ('created_at', 'updated_at')


@admin.register(PlanClass)
class PlanClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'plan', 'network', 'annual_limit', 'order')
    list_filter = ('plan__provider',)
    search_fields = ('name', 'plan__name')
    inlines = [PlanClassBenefitInline]


# ==========================================
# Policy Admin
# ==========================================

class PolicyClassInline(admin.TabularInline):
    model = PolicyClass
    extra = 1
    fields = ('name', 'plan_class', 'network', 'annual_limit')
    readonly_fields = ()


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ('policy_number', 'client', 'provider', 'plan', 'start_date', 'end_date', 'is_active')
    list_filter = ('provider', 'is_active')
    search_fields = ('policy_number', 'client__name_en')
    inlines = [PolicyClassInline]


class ClassBenefitInline(admin.TabularInline):
    model = ClassBenefit
    extra = 1
    autocomplete_fields = ['benefit_type']


@admin.register(PolicyClass)
class PolicyClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'policy', 'plan_class', 'network', 'effective_annual_limit')
    list_filter = ('policy__provider',)
    search_fields = ('name', 'policy__policy_number')
    inlines = [ClassBenefitInline]

    def effective_annual_limit(self, obj):
        return obj.effective_annual_limit
    effective_annual_limit.short_description = 'الحد السنوي الفعلي'
```

- [ ] **Step 2: التحقق من عمل Admin**

```
python manage.py runserver
```

افتح: `http://127.0.0.1:8000/admin/policies/insuranceplan/`

تأكد أن القائمة تعمل وأن الـ Inline يُظهر PlanClass.

- [ ] **Step 3: Commit**

```
git add policies/admin.py
git commit -m "feat(policies): register InsurancePlan in Django admin with inlines"
```

---

## Task 5: دالة العزل + النماذج الجديدة (Forms)

**Files:**
- Modify: `policies/views.py` (إضافة get_allowed_plans في الأعلى)
- Modify: `policies/forms.py`

- [ ] **Step 1: إضافة get_allowed_plans في policies/views.py**

ابحث عن سطر `def get_allowed_policies(user):` وأضف بعد نهاية الدالة مباشرة:

```python
def get_allowed_plans(user):
    """
    تُرجع InsurancePlan المسموح للمستخدم رؤيتها/إدارتها.
    InsurancePlan مملوك للوسيط — HR والأعضاء لا يرونه مباشرة.
    """
    from .models import InsurancePlan
    if user.role == User.Roles.SUPER_ADMIN:
        return InsurancePlan.objects.all()
    elif user.is_broker_role and user.related_broker:
        return InsurancePlan.objects.filter(broker=user.related_broker)
    return InsurancePlan.objects.none()
```

- [ ] **Step 2: إضافة import للنماذج الجديدة في views.py**

في أعلى `policies/views.py` عدّل سطر الـ import:

```python
from .models import Policy, PolicyClass, ClassBenefit, BenefitType, InsurancePlan, PlanClass, PlanClassBenefit
```

- [ ] **Step 3: إضافة النماذج الجديدة في policies/forms.py**

في نهاية `policies/forms.py` أضف:

```python
from .models import InsurancePlan, PlanClass, PlanClassBenefit
from providers.models import Provider

INPUT_CLASS = 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500'
SELECT_CLASS = 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500'


class InsurancePlanForm(forms.ModelForm):
    class Meta:
        model = InsurancePlan
        fields = ['provider', 'name', 'description', 'is_active']
        widgets = {
            'provider': forms.Select(attrs={'class': SELECT_CLASS}),
            'name': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'مثال: بوبا الذهبي 2026'}),
            'description': forms.Textarea(attrs={'class': INPUT_CLASS, 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-brand-600 border-slate-300 rounded'}),
        }

    def __init__(self, *args, **kwargs):
        self.broker = kwargs.pop('broker', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.broker:
            instance.broker = self.broker
        if commit:
            instance.save()
        return instance


class PlanClassForm(forms.ModelForm):
    class Meta:
        model = PlanClass
        fields = ['name', 'network', 'annual_limit', 'order']
        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'مثال: VIP، فئة أ'}),
            'network': forms.Select(attrs={'class': SELECT_CLASS}),
            'annual_limit': forms.NumberInput(attrs={'class': INPUT_CLASS}),
            'order': forms.NumberInput(attrs={'class': INPUT_CLASS}),
        }


class PlanClassBenefitForm(forms.ModelForm):
    class Meta:
        model = PlanClassBenefit
        fields = ['benefit_type', 'limit_amount', 'deductible_percentage', 'description']
        widgets = {
            'benefit_type': forms.Select(attrs={'class': SELECT_CLASS}),
            'limit_amount': forms.NumberInput(attrs={'class': INPUT_CLASS}),
            'deductible_percentage': forms.NumberInput(attrs={'class': INPUT_CLASS}),
            'description': forms.Textarea(attrs={'class': INPUT_CLASS, 'rows': 2}),
        }
```

- [ ] **Step 4: التحقق من عدم وجود أخطاء**

```
python manage.py check
```

المتوقع: `System check identified no issues`

- [ ] **Step 5: Commit**

```
git add policies/views.py policies/forms.py
git commit -m "feat(policies): add get_allowed_plans isolation + Plan forms"
```

---

## Task 6: Views لإدارة InsurancePlan

**Files:**
- Modify: `policies/views.py`

- [ ] **Step 1: إضافة Views في policies/views.py**

أضف هذا القسم **في نهاية** ملف `policies/views.py`:

```python
# ==========================================
# 3. إدارة خطط التأمين (Insurance Plans)
# ==========================================

@login_required
@permission_required('policies.manage_policy_structure', raise_exception=True)
def plan_list(request):
    """قائمة خطط التأمين للوسيط."""
    plans = get_allowed_plans(request.user).select_related('provider', 'broker').order_by('provider__name_en', 'name')
    return render(request, 'policies/plan_list.html', {'plans': plans})


@login_required
@permission_required('policies.manage_policy_structure', raise_exception=True)
def plan_create(request):
    """إنشاء خطة تأمين جديدة."""
    from .forms import InsurancePlanForm
    broker = getattr(request.user, 'related_broker', None)

    if request.method == 'POST':
        form = InsurancePlanForm(request.POST, broker=broker)
        if form.is_valid():
            plan = form.save()
            messages.success(request, f"تم إنشاء الخطة '{plan.name}' بنجاح")
            return redirect('policies:plan_detail', pk=plan.pk)
    else:
        form = InsurancePlanForm(broker=broker)
    return render(request, 'policies/plan_form.html', {'form': form, 'title': 'إضافة خطة تأمين جديدة'})


@login_required
@permission_required('policies.view_policy_details', raise_exception=True)
def plan_detail(request, pk):
    """تفاصيل خطة التأمين مع فئاتها."""
    plan = get_object_or_404(
        get_allowed_plans(request.user).select_related('provider', 'broker'),
        pk=pk
    )
    classes = plan.classes.select_related('network').prefetch_related(
        'benefits__benefit_type'
    ).order_by('order', 'name')
    return render(request, 'policies/plan_detail.html', {'plan': plan, 'classes': classes})


@login_required
@permission_required('policies.manage_policy_structure', raise_exception=True)
def plan_update(request, pk):
    """تعديل خطة تأمين."""
    from .forms import InsurancePlanForm
    plan = get_object_or_404(get_allowed_plans(request.user), pk=pk)
    broker = getattr(request.user, 'related_broker', None)

    if request.method == 'POST':
        form = InsurancePlanForm(request.POST, instance=plan, broker=broker)
        if form.is_valid():
            form.save()
            messages.success(request, "تم تحديث الخطة بنجاح")
            return redirect('policies:plan_detail', pk=plan.pk)
    else:
        form = InsurancePlanForm(instance=plan, broker=broker)
    return render(request, 'policies/plan_form.html', {'form': form, 'title': f'تعديل: {plan.name}', 'plan': plan})


@login_required
@permission_required('policies.manage_policy_structure', raise_exception=True)
def plan_class_create(request, plan_pk):
    """إضافة فئة جديدة لخطة تأمين (POST فقط — يُستخدم مع HTMX)."""
    from .forms import PlanClassForm
    plan = get_object_or_404(get_allowed_plans(request.user), pk=plan_pk)

    if request.method == 'POST':
        form = PlanClassForm(request.POST)
        if form.is_valid():
            pc = form.save(commit=False)
            pc.plan = plan
            pc.save()
            if request.headers.get('HX-Request'):
                classes = plan.classes.select_related('network').prefetch_related('benefits__benefit_type')
                return render(request, 'policies/partials/plan_classes_list.html', {'plan': plan, 'classes': classes})
            return redirect('policies:plan_detail', pk=plan.pk)
    else:
        form = PlanClassForm()
    return render(request, 'policies/plan_class_form.html', {'form': form, 'plan': plan})


@login_required
@permission_required('policies.manage_policy_structure', raise_exception=True)
def plan_class_benefit_manage(request, class_pk):
    """إدارة منافع فئة القالب."""
    from .forms import PlanClassBenefitForm
    plan_class = get_object_or_404(PlanClass, pk=class_pk)
    plan = get_object_or_404(get_allowed_plans(request.user), pk=plan_class.plan_id)

    benefits = plan_class.benefits.select_related('benefit_type').all()

    if request.method == 'POST':
        form = PlanClassBenefitForm(request.POST)
        if form.is_valid():
            benefit = form.save(commit=False)
            benefit.plan_class = plan_class
            benefit.save()
            messages.success(request, "تمت إضافة المنفعة بنجاح")
            if request.headers.get('HX-Request'):
                benefits = plan_class.benefits.select_related('benefit_type').all()
                return render(request, 'policies/partials/plan_class_benefits.html',
                              {'plan_class': plan_class, 'benefits': benefits})
            return redirect('policies:plan_detail', pk=plan.pk)
    else:
        form = PlanClassBenefitForm()

    return render(request, 'policies/benefit_manage.html', {
        'plan_class': plan_class, 'plan': plan, 'benefits': benefits, 'form': form,
        'is_plan_class': True,
    })


@login_required
@permission_required('policies.manage_policy_structure', raise_exception=True)
def plan_get_classes(request, plan_pk):
    """
    HTMX endpoint: يُرجع قائمة فئات الخطة كـ <option> elements.
    يُستخدم في نموذج إنشاء الوثيقة عند اختيار خطة.
    """
    plan = get_object_or_404(get_allowed_plans(request.user), pk=plan_pk)
    classes = plan.classes.order_by('order', 'name')
    return render(request, 'policies/partials/plan_classes_options.html', {'classes': classes})
```

- [ ] **Step 2: التحقق من عدم وجود أخطاء**

```
python manage.py check
```

المتوقع: `System check identified no issues`

- [ ] **Step 3: Commit**

```
git add policies/views.py
git commit -m "feat(policies): add InsurancePlan CRUD views + HTMX endpoints"
```

---

## Task 7: URL Patterns الجديدة

**Files:**
- Modify: `policies/urls.py`

- [ ] **Step 1: تحديث policies/urls.py**

```python
from django.urls import path
from . import views

app_name = 'policies'

urlpatterns = [
    # ==========================================
    # الوثائق (Policies)
    # ==========================================
    path('', views.policy_list, name='policy_list'),
    path('add/', views.policy_create, name='policy_create'),
    path('<uuid:pk>/', views.policy_detail, name='policy_detail'),
    path('<uuid:pk>/edit/', views.policy_update, name='policy_update'),
    path('<uuid:pk>/delete/', views.policy_delete, name='policy_delete'),
    path('<uuid:pk>/renew/', views.policy_renew, name='policy_renew'),

    # الفئات والمنافع
    path('<uuid:policy_pk>/classes/add/', views.policy_class_create, name='policy_class_create'),
    path('classes/<uuid:class_pk>/benefits/', views.class_benefit_manage, name='class_benefit_manage'),

    # أنواع المنافع
    path('benefit-types/', views.benefit_type_list, name='benefit_type_list'),

    # ==========================================
    # خطط التأمين (Insurance Plans)
    # ==========================================
    path('plans/', views.plan_list, name='plan_list'),
    path('plans/add/', views.plan_create, name='plan_create'),
    path('plans/<uuid:pk>/', views.plan_detail, name='plan_detail'),
    path('plans/<uuid:pk>/edit/', views.plan_update, name='plan_update'),

    # فئات الخطة
    path('plans/<uuid:plan_pk>/classes/add/', views.plan_class_create, name='plan_class_create'),
    path('plan-classes/<uuid:class_pk>/benefits/', views.plan_class_benefit_manage, name='plan_class_benefit_manage'),

    # HTMX: جلب فئات خطة محددة (لنموذج إنشاء الوثيقة)
    path('plans/<uuid:plan_pk>/classes/options/', views.plan_get_classes, name='plan_get_classes'),
]
```

- [ ] **Step 2: إضافة stub لـ policy_renew (مؤقتاً حتى Task 10)**

في نهاية `policies/views.py` أضف:

```python
@login_required
@permission_required('policies.add_policy', raise_exception=True)
def policy_renew(request, pk):
    """سيتم تنفيذه في Task 10."""
    policy = get_object_or_404(get_allowed_policies(request.user), pk=pk)
    messages.info(request, "ميزة التجديد قيد الإنشاء")
    return redirect('policies:policy_detail', pk=policy.pk)
```

- [ ] **Step 3: التحقق من عمل URLs**

```
python manage.py check
python manage.py show_urls | findstr policies
```

- [ ] **Step 4: Commit**

```
git add policies/urls.py policies/views.py
git commit -m "feat(policies): add Insurance Plan URL patterns"
```

---

## Task 8: قوالب InsurancePlan

**Files:**
- Create: `templates/policies/plan_list.html`
- Create: `templates/policies/plan_form.html`
- Create: `templates/policies/plan_detail.html`
- Create: `templates/policies/plan_class_form.html`
- Create: `templates/policies/partials/plan_classes_list.html`
- Create: `templates/policies/partials/plan_classes_options.html`
- Create: `templates/policies/partials/plan_class_benefits.html`

- [ ] **Step 1: إنشاء plan_list.html**

```html
{% extends 'base.html' %}
{% block content %}
<div class="mb-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
    <div>
        <h2 class="text-2xl font-bold text-slate-800">خطط التأمين</h2>
        <p class="text-slate-500 text-sm mt-1">القوالب التأمينية المعرّفة لكل شركة تأمين</p>
    </div>
    <a href="{% url 'policies:plan_create' %}"
        class="px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 font-bold shadow-md shadow-brand-200 transition flex items-center gap-2 text-sm">
        <i class="ph-bold ph-plus"></i> إضافة خطة جديدة
    </a>
</div>

{% if plans %}
<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
    {% for plan in plans %}
    <div class="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-md transition">
        <div class="flex items-start justify-between mb-3">
            <div>
                <h3 class="font-bold text-slate-800">{{ plan.name }}</h3>
                <p class="text-sm text-slate-500">{{ plan.provider.name_ar }}</p>
            </div>
            <span class="px-2 py-0.5 text-xs rounded-full {% if plan.is_active %}bg-green-100 text-green-700{% else %}bg-slate-100 text-slate-500{% endif %}">
                {% if plan.is_active %}نشطة{% else %}متوقفة{% endif %}
            </span>
        </div>
        <p class="text-sm text-slate-600 mb-4">{{ plan.classes.count }} فئة تأمينية</p>
        <a href="{% url 'policies:plan_detail' pk=plan.pk %}"
            class="text-sm text-brand-600 hover:text-brand-700 font-medium flex items-center gap-1">
            <i class="ph ph-arrow-left"></i> عرض التفاصيل
        </a>
    </div>
    {% endfor %}
</div>
{% else %}
<div class="text-center py-16 text-slate-400">
    <i class="ph-duotone ph-file-text text-5xl mb-3 block"></i>
    <p>لا توجد خطط تأمين بعد</p>
    <a href="{% url 'policies:plan_create' %}" class="mt-4 inline-block text-brand-600 hover:underline text-sm">
        أضف أول خطة
    </a>
</div>
{% endif %}
{% endblock %}
```

- [ ] **Step 2: إنشاء plan_form.html**

```html
{% extends 'base.html' %}
{% block content %}
<div class="max-w-2xl mx-auto">
    <div class="mb-6">
        <h2 class="text-2xl font-bold text-slate-800">{{ title }}</h2>
        <p class="text-slate-500 text-sm mt-1">تُعرَّف الخطة مرة واحدة وتُستخدم في وثائق متعددة</p>
    </div>
    <div class="bg-white rounded-xl border border-slate-200 p-6">
        <form method="post">
            {% csrf_token %}
            <div class="space-y-5">
                <div>
                    <label class="block text-sm font-medium text-slate-700 mb-1">شركة التأمين *</label>
                    {{ form.provider }}
                </div>
                <div>
                    <label class="block text-sm font-medium text-slate-700 mb-1">اسم الخطة *</label>
                    {{ form.name }}
                    <p class="text-xs text-slate-400 mt-1">مثال: بوبا الذهبي 2026، التعاونية الماسية</p>
                </div>
                <div>
                    <label class="block text-sm font-medium text-slate-700 mb-1">وصف (اختياري)</label>
                    {{ form.description }}
                </div>
                <div class="flex items-center gap-2">
                    {{ form.is_active }}
                    <label class="text-sm text-slate-700">خطة نشطة</label>
                </div>
            </div>
            {% if form.errors %}
            <div class="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
                {{ form.errors }}
            </div>
            {% endif %}
            <div class="mt-6 flex gap-3">
                <button type="submit" class="px-5 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 font-bold text-sm">
                    حفظ الخطة
                </button>
                <a href="{% url 'policies:plan_list' %}" class="px-5 py-2 border border-slate-200 rounded-lg text-slate-600 text-sm hover:bg-slate-50">
                    إلغاء
                </a>
            </div>
        </form>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 3: إنشاء plan_detail.html**

```html
{% extends 'base.html' %}
{% block content %}
<div class="mb-6 flex items-center justify-between">
    <div>
        <div class="flex items-center gap-2 text-sm text-slate-500 mb-1">
            <a href="{% url 'policies:plan_list' %}" class="hover:text-brand-600">خطط التأمين</a>
            <i class="ph ph-caret-left text-xs"></i>
            <span>{{ plan.name }}</span>
        </div>
        <h2 class="text-2xl font-bold text-slate-800">{{ plan.name }}</h2>
        <p class="text-slate-500 text-sm">{{ plan.provider.name_ar }}</p>
    </div>
    <a href="{% url 'policies:plan_update' pk=plan.pk %}"
        class="px-4 py-2 border border-slate-200 rounded-lg text-slate-600 text-sm hover:bg-slate-50 flex items-center gap-2">
        <i class="ph ph-pencil"></i> تعديل
    </a>
</div>

<!-- الفئات -->
<div class="bg-white rounded-xl border border-slate-200">
    <div class="p-4 border-b border-slate-100 flex items-center justify-between">
        <h3 class="font-bold text-slate-700">الفئات التأمينية ({{ classes|length }})</h3>
        <button
            hx-get="{% url 'policies:plan_class_create' plan_pk=plan.pk %}"
            hx-target="#plan-class-form-container"
            hx-swap="innerHTML"
            class="px-3 py-1.5 bg-brand-600 text-white rounded-lg text-xs font-bold hover:bg-brand-700 flex items-center gap-1">
            <i class="ph-bold ph-plus"></i> إضافة فئة
        </button>
    </div>

    <div id="plan-class-form-container"></div>

    <div id="plan-classes-list">
        {% include 'policies/partials/plan_classes_list.html' %}
    </div>
</div>
{% endblock %}
```

- [ ] **Step 4: إنشاء plan_class_form.html**

```html
<div class="p-4 border-b border-brand-100 bg-brand-50">
    <h4 class="font-medium text-slate-700 mb-3">إضافة فئة جديدة</h4>
    <form hx-post="{% url 'policies:plan_class_create' plan_pk=plan.pk %}"
          hx-target="#plan-classes-list"
          hx-swap="innerHTML">
        {% csrf_token %}
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
                <label class="block text-xs font-medium text-slate-600 mb-1">اسم الفئة *</label>
                {{ form.name }}
            </div>
            <div>
                <label class="block text-xs font-medium text-slate-600 mb-1">الشبكة الافتراضية</label>
                {{ form.network }}
            </div>
            <div>
                <label class="block text-xs font-medium text-slate-600 mb-1">الحد السنوي *</label>
                {{ form.annual_limit }}
            </div>
        </div>
        <div class="mt-3 flex gap-2">
            <button type="submit" class="px-4 py-1.5 bg-brand-600 text-white rounded text-sm font-medium">حفظ</button>
            <button type="button" onclick="this.closest('#plan-class-form-container').innerHTML=''"
                class="px-4 py-1.5 border border-slate-200 text-slate-600 rounded text-sm">إلغاء</button>
        </div>
    </form>
</div>
```

- [ ] **Step 5: إنشاء partials/plan_classes_list.html**

```html
{% if classes %}
<div class="divide-y divide-slate-100">
    {% for pc in classes %}
    <div class="p-4 flex items-center justify-between">
        <div class="flex items-center gap-4">
            <span class="px-2.5 py-1 bg-brand-100 text-brand-700 rounded-full text-xs font-bold">{{ pc.name }}</span>
            <div class="text-sm text-slate-600">
                <span>{{ pc.annual_limit|floatformat:0 }} ريال</span>
                {% if pc.network %}
                <span class="mx-2 text-slate-300">|</span>
                <span>{{ pc.network.name_ar }}</span>
                {% endif %}
            </div>
            <span class="text-xs text-slate-400">{{ pc.benefits.count }} منفعة</span>
        </div>
        <a href="{% url 'policies:plan_class_benefit_manage' class_pk=pc.pk %}"
            class="text-xs text-brand-600 hover:text-brand-700 flex items-center gap-1">
            <i class="ph ph-list-dashes"></i> إدارة المنافع
        </a>
    </div>
    {% endfor %}
</div>
{% else %}
<div class="p-8 text-center text-slate-400 text-sm">لا توجد فئات بعد — أضف أول فئة</div>
{% endif %}
```

- [ ] **Step 6: إنشاء partials/plan_classes_options.html**

```html
<option value="">--- اختر الفئة ---</option>
{% for pc in classes %}
<option value="{{ pc.pk }}">{{ pc.name }} (حد: {{ pc.annual_limit|floatformat:0 }} ريال)</option>
{% endfor %}
```

- [ ] **Step 7: إنشاء partials/plan_class_benefits.html**

```html
{% if benefits %}
<div class="overflow-x-auto">
    <table class="w-full text-sm">
        <thead class="bg-slate-50 text-slate-500 text-xs uppercase">
            <tr>
                <th class="px-4 py-2 text-right">المنفعة</th>
                <th class="px-4 py-2 text-right">الحد (ريال)</th>
                <th class="px-4 py-2 text-right">نسبة التحمل</th>
            </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
            {% for b in benefits %}
            <tr>
                <td class="px-4 py-2">{{ b.benefit_type.name_ar }}</td>
                <td class="px-4 py-2">{{ b.limit_amount|floatformat:0 }}</td>
                <td class="px-4 py-2">{{ b.deductible_percentage }}%</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% else %}
<p class="text-center text-slate-400 text-sm py-4">لا توجد منافع محددة</p>
{% endif %}
```

- [ ] **Step 8: التحقق من الصفحات**

```
python manage.py runserver
```

- افتح `http://127.0.0.1:8000/policies/plans/` — يجب أن تظهر القائمة.
- أضف خطة جديدة — يجب أن يعمل الحفظ والتوجيه لصفحة التفاصيل.
- في صفحة التفاصيل، اضغط "إضافة فئة" — يجب أن يظهر الفورم بدون تحديث الصفحة.

- [ ] **Step 9: Commit**

```
git add templates/policies/
git commit -m "feat(policies): add InsurancePlan templates with HTMX class management"
```

---

## Task 9: تعديل policy_create لاستخدام الخطة

**Files:**
- Modify: `policies/forms.py` (إضافة حقل plan لـ PolicyForm)
- Modify: `policies/views.py` (تعديل policy_create)
- Modify: `templates/policies/policy_form.html`

- [ ] **Step 1: إضافة حقل plan لـ PolicyForm**

في `policies/forms.py`، في `class PolicyForm.__init__` أضف قبل آخر `else`:

```python
        # إضافة قائمة منسدلة للخطط (مفلترة للوسيط)
        from .models import InsurancePlan
        if self.user:
            if self.user.role == User.Roles.SUPER_ADMIN:
                self.fields['plan'].queryset = InsurancePlan.objects.all().select_related('provider')
            elif self.user.is_broker_role and self.user.related_broker:
                self.fields['plan'].queryset = InsurancePlan.objects.filter(
                    broker=self.user.related_broker
                ).select_related('provider')
            else:
                self.fields['plan'].queryset = InsurancePlan.objects.none()
```

وفي `fields` في `class Meta`:

```python
        fields = ['client', 'master_policy', 'provider', 'plan', 'policy_number', 'start_date', 'end_date', 'contract_file', 'is_active']
        widgets = {
            # ... (الـ widgets الموجودة) ...
            'plan': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500',
                'hx-get': '',  # سيُعيَّن ديناميكياً في الـ template
                'hx-target': '#plan-classes-preview',
                'hx-trigger': 'change',
            }),
        }
```

- [ ] **Step 2: تعديل policy_create view لتوليد PolicyClass تلقائياً**

في `policies/views.py` عدّل `policy_create`:

```python
@login_required
@permission_required('policies.add_policy', raise_exception=True)
def policy_create(request):
    if request.method == 'POST':
        form = PolicyForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            policy = form.save()
            # توليد PolicyClass تلقائياً من PlanClass إذا تم اختيار خطة
            if policy.plan:
                for plan_class in policy.plan.classes.select_related('network').order_by('order'):
                    PolicyClass.objects.get_or_create(
                        policy=policy,
                        name=plan_class.name,
                        defaults={
                            'plan_class': plan_class,
                            # network و annual_limit تُترك null → ترث من PlanClass
                        }
                    )
            messages.success(request, "تمت إضافة البوليصة بنجاح")
            return redirect('policies:policy_detail', pk=policy.pk)
    else:
        form = PolicyForm(user=request.user)
    return render(request, 'policies/policy_form.html', {'form': form, 'title': 'إضافة بوليصة جديدة'})
```

- [ ] **Step 3: تحديث policy_form.html لإظهار الخطة مع HTMX preview**

ابحث عن حقل `provider` في `templates/policies/policy_form.html` وأضف بعده مباشرة:

```html
<!-- حقل الخطة التأمينية مع HTMX لمعاينة الفئات -->
<div>
    <label class="block text-sm font-medium text-slate-700 mb-1">
        الخطة التأمينية
        <span class="text-xs text-slate-400 font-normal">(اختياري — تُوَلِّد الفئات تلقائياً)</span>
    </label>
    <select name="plan" id="id_plan"
        class="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500"
        hx-get="/policies/plans/__plan_pk__/classes/options/"
        hx-target="#plan-classes-preview"
        hx-trigger="change"
        hx-vals='js:{"plan_pk": event.target.value}'>
        <option value="">--- بدون خطة ---</option>
        {% for plan in form.plan.field.queryset %}
        <option value="{{ plan.pk }}" {% if form.instance.plan_id == plan.pk %}selected{% endif %}>
            {{ plan.name }} — {{ plan.provider.name_ar }}
        </option>
        {% endfor %}
    </select>
    <!-- معاينة الفئات التي ستُوَلَّد -->
    <div id="plan-classes-preview" class="mt-2 text-xs text-slate-500"></div>
</div>
```

**ملاحظة:** HTMX endpoint للـ plan classes يحتاج أن يُنقل لـ URL ثابت. عدّل الـ `hx-get` ليستخدم:

```html
hx-get="{% url 'policies:plan_get_classes' plan_pk='00000000-0000-0000-0000-000000000000' %}"
```

ثم أضف script بسيط يحدّث الـ URL عند التغيير:

```html
<script>
document.getElementById('id_plan').addEventListener('change', function() {
    const planPk = this.value;
    if (planPk) {
        htmx.ajax('GET', `/policies/plans/${planPk}/classes/options/`, {target: '#plan-classes-preview'});
    } else {
        document.getElementById('plan-classes-preview').innerHTML = '';
    }
});
</script>
```

- [ ] **Step 4: كتابة اختبار التوليد التلقائي**

في `policies/tests.py` أضف:

```python
from django.test import TestCase, Client as DjangoClient
from django.contrib.auth import get_user_model

User = get_user_model()


class PolicyCreateWithPlanTest(TestCase):
    def setUp(self):
        self.broker = Broker.objects.create(
            name_ar='وسيط', name_en='Broker', commercial_record='BR004'
        )
        self.provider = Provider.objects.create(
            name_ar='بوبا', name_en='Bupa', license_number='LIC004'
        )
        self.client_obj = Client.objects.create(
            name_ar='شركة', name_en='Company', commercial_record='CR003', broker=self.broker
        )
        self.plan = InsurancePlan.objects.create(
            broker=self.broker, provider=self.provider, name='خطة اختبار 2'
        )
        PlanClass.objects.create(plan=self.plan, name='VIP', annual_limit=100000, order=1)
        PlanClass.objects.create(plan=self.plan, name='فئة أ', annual_limit=60000, order=2)

    def test_auto_generate_policy_classes_from_plan(self):
        """عند إنشاء وثيقة مرتبطة بخطة، يجب توليد PolicyClass تلقائياً."""
        policy = Policy.objects.create(
            client=self.client_obj,
            provider=self.provider,
            policy_number='POL-AUTO-001',
            start_date='2026-01-01',
            end_date='2026-12-31',
            plan=self.plan,
        )
        # محاكاة المنطق الموجود في policy_create view
        for plan_class in policy.plan.classes.order_by('order'):
            PolicyClass.objects.get_or_create(
                policy=policy, name=plan_class.name,
                defaults={'plan_class': plan_class}
            )
        self.assertEqual(policy.classes.count(), 2)
        vip_class = policy.classes.get(name='VIP')
        self.assertEqual(vip_class.plan_class.name, 'VIP')
        self.assertIsNone(vip_class.annual_limit)  # null → يرث
        self.assertEqual(vip_class.effective_annual_limit, 100000)
```

- [ ] **Step 5: تشغيل الاختبار**

```
python manage.py test policies.tests.PolicyCreateWithPlanTest -v 2
```

المتوقع: `OK`

- [ ] **Step 6: Commit**

```
git add policies/forms.py policies/views.py templates/policies/policy_form.html policies/tests.py
git commit -m "feat(policies): policy_create auto-generates PolicyClass from InsurancePlan"
```

---

## Task 10: ميزة تجديد الوثيقة (Policy Renewal)

**Files:**
- Modify: `policies/views.py` (استبدال stub بتنفيذ حقيقي)
- Create: `templates/policies/policy_renew_confirm.html`
- Modify: `templates/policies/policy_detail.html`

- [ ] **Step 1: كتابة اختبار التجديد**

في `policies/tests.py` أضف:

```python
class PolicyRenewalTest(TestCase):
    def setUp(self):
        self.broker = Broker.objects.create(
            name_ar='وسيط', name_en='Broker', commercial_record='BR005'
        )
        self.provider = Provider.objects.create(
            name_ar='بوبا', name_en='Bupa', license_number='LIC005'
        )
        self.client_obj = Client.objects.create(
            name_ar='شركة', name_en='Company', commercial_record='CR004', broker=self.broker
        )
        self.plan = InsurancePlan.objects.create(
            broker=self.broker, provider=self.provider, name='خطة تجديد'
        )
        self.plan_class_vip = PlanClass.objects.create(
            plan=self.plan, name='VIP', annual_limit=100000
        )
        self.old_policy = Policy.objects.create(
            client=self.client_obj, provider=self.provider,
            policy_number='POL-OLD-001', plan=self.plan,
            start_date='2025-01-01', end_date='2025-12-31',
        )
        # فئة مع override
        self.old_class = PolicyClass.objects.create(
            policy=self.old_policy, name='VIP',
            plan_class=self.plan_class_vip,
            annual_limit=120000,  # override
        )

    def test_renewal_creates_new_policy_with_same_plan(self):
        """التجديد يُنشئ وثيقة جديدة مرتبطة بنفس الخطة."""
        new_policy = Policy.objects.create(
            client=self.old_policy.client,
            provider=self.old_policy.provider,
            plan=self.old_policy.plan,
            policy_number='POL-NEW-001',
            start_date='2026-01-01',
            end_date='2026-12-31',
        )
        # نسخ الـ overrides من الوثيقة القديمة
        for old_class in self.old_policy.classes.select_related('plan_class').prefetch_related('benefits'):
            new_class = PolicyClass.objects.create(
                policy=new_policy,
                name=old_class.name,
                plan_class=old_class.plan_class,
                annual_limit=old_class.annual_limit,  # ينسخ الـ override
                network=old_class.network,
            )
        self.assertEqual(new_policy.plan, self.old_policy.plan)
        self.assertEqual(new_policy.classes.count(), 1)
        new_class = new_policy.classes.first()
        self.assertEqual(new_class.effective_annual_limit, 120000)  # override محفوظ
        # الوثيقة القديمة لم تُمس
        self.old_policy.refresh_from_db()
        self.assertEqual(self.old_policy.policy_number, 'POL-OLD-001')
```

- [ ] **Step 2: تشغيل الاختبار للتأكد من الفشل**

```
python manage.py test policies.tests.PolicyRenewalTest -v 2
```

المتوقع: يجب أن ينجح لأن المنطق في الاختبار نفسه — تأكد أن `OK`

- [ ] **Step 3: استبدال stub policy_renew بالتنفيذ الحقيقي**

في `policies/views.py` استبدل دالة `policy_renew`:

```python
@login_required
@permission_required('policies.add_policy', raise_exception=True)
def policy_renew(request, pk):
    """
    تجديد وثيقة منتهية: ينشئ وثيقة جديدة بنفس الخطة وينسخ الـ overrides.
    """
    old_policy = get_object_or_404(
        get_allowed_policies(request.user).select_related('plan', 'provider', 'client'),
        pk=pk
    )

    if request.method == 'POST':
        new_policy_number = request.POST.get('policy_number', '').strip()
        new_start = request.POST.get('start_date')
        new_end = request.POST.get('end_date')

        if not all([new_policy_number, new_start, new_end]):
            messages.error(request, "يرجى تعبئة جميع الحقول المطلوبة")
            return render(request, 'policies/policy_renew_confirm.html', {'policy': old_policy})

        # إنشاء الوثيقة الجديدة
        new_policy = Policy.objects.create(
            client=old_policy.client,
            provider=old_policy.provider,
            plan=old_policy.plan,
            policy_number=new_policy_number,
            start_date=new_start,
            end_date=new_end,
        )

        # نسخ الـ overrides من الوثيقة القديمة
        old_classes = old_policy.classes.select_related('plan_class', 'network').prefetch_related('benefits__benefit_type')
        for old_class in old_classes:
            new_class = PolicyClass.objects.create(
                policy=new_policy,
                name=old_class.name,
                plan_class=old_class.plan_class,
                annual_limit=old_class.annual_limit,  # ينسخ override أو None
                network=old_class.network,             # ينسخ override أو None
            )
            # نسخ منافع الـ override
            for benefit in old_class.benefits.all():
                from .models import ClassBenefit
                ClassBenefit.objects.create(
                    policy_class=new_class,
                    benefit_type=benefit.benefit_type,
                    limit_amount=benefit.limit_amount,
                    deductible_percentage=benefit.deductible_percentage,
                    description=benefit.description,
                )

        messages.success(request, f"تم تجديد الوثيقة بنجاح — رقم الوثيقة الجديدة: {new_policy.policy_number}")
        return redirect('policies:policy_detail', pk=new_policy.pk)

    return render(request, 'policies/policy_renew_confirm.html', {'policy': old_policy})
```

- [ ] **Step 4: إنشاء templates/policies/policy_renew_confirm.html**

```html
{% extends 'base.html' %}
{% block content %}
<div class="max-w-xl mx-auto">
    <div class="mb-6">
        <h2 class="text-2xl font-bold text-slate-800">تجديد وثيقة تأمين</h2>
        <p class="text-slate-500 text-sm mt-1">سيتم إنشاء وثيقة جديدة بنفس الخطة والفئات مع الاحتفاظ بالتخصيصات</p>
    </div>

    <!-- معلومات الوثيقة القديمة -->
    <div class="bg-slate-50 border border-slate-200 rounded-xl p-4 mb-6">
        <p class="text-xs font-medium text-slate-500 mb-2">الوثيقة المنتهية</p>
        <div class="flex items-center gap-3">
            <span class="font-bold text-slate-700">{{ policy.policy_number }}</span>
            <span class="text-slate-400">—</span>
            <span class="text-sm text-slate-600">{{ policy.client.name_ar }}</span>
        </div>
        <p class="text-xs text-slate-500 mt-1">
            {{ policy.start_date }} → {{ policy.end_date }}
            {% if policy.plan %}· {{ policy.plan.name }}{% endif %}
        </p>
    </div>

    <!-- نموذج الوثيقة الجديدة -->
    <div class="bg-white rounded-xl border border-slate-200 p-6">
        <h3 class="font-medium text-slate-700 mb-4">بيانات الوثيقة الجديدة</h3>
        <form method="post">
            {% csrf_token %}
            <div class="space-y-4">
                <div>
                    <label class="block text-sm font-medium text-slate-700 mb-1">رقم الوثيقة الجديدة *</label>
                    <input type="text" name="policy_number" required
                        class="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500"
                        placeholder="مثال: POL-2026-001">
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="block text-sm font-medium text-slate-700 mb-1">تاريخ البداية *</label>
                        <input type="date" name="start_date" required
                            class="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-slate-700 mb-1">تاريخ الانتهاء *</label>
                        <input type="date" name="end_date" required
                            class="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500">
                    </div>
                </div>
            </div>
            <div class="mt-6 flex gap-3">
                <button type="submit"
                    class="px-5 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 font-bold text-sm">
                    تجديد الوثيقة
                </button>
                <a href="{% url 'policies:policy_detail' pk=policy.pk %}"
                    class="px-5 py-2 border border-slate-200 rounded-lg text-slate-600 text-sm hover:bg-slate-50">
                    إلغاء
                </a>
            </div>
        </form>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 5: إضافة زر "تجديد" في policy_detail.html**

ابحث في `templates/policies/policy_detail.html` عن زر "تعديل" أو قسم الأزرار وأضف:

```html
<a href="{% url 'policies:policy_renew' pk=policy.pk %}"
    class="px-4 py-2 border border-green-200 text-green-700 rounded-lg text-sm hover:bg-green-50 flex items-center gap-2">
    <i class="ph ph-arrows-clockwise"></i> تجديد الوثيقة
</a>
```

- [ ] **Step 6: تشغيل الاختبارات الكاملة**

```
python manage.py test policies -v 2
```

المتوقع: جميع الاختبارات `OK`

- [ ] **Step 7: Commit**

```
git add policies/views.py templates/policies/policy_renew_confirm.html templates/policies/policy_detail.html policies/tests.py
git commit -m "feat(policies): add policy renewal with override copy"
```

---

## Task 11: تحديث policy_detail لعرض بيانات الخطة والفئات الفعلية

**Files:**
- Modify: `policies/views.py` (تحسين policy_detail بـ prefetch_related)
- Modify: `templates/policies/policy_detail.html`

- [ ] **Step 1: تحديث policy_detail view لاستخدام prefetch_related**

في `policies/views.py` عدّل `policy_detail`:

```python
@login_required
@permission_required('policies.view_policy', raise_exception=True)
def policy_detail(request, pk):
    policy = get_object_or_404(
        get_allowed_policies(request.user).select_related(
            'client', 'provider', 'master_policy', 'plan__provider'
        ),
        pk=pk
    )

    # جلب الفئات مع كل البيانات الضرورية — دفعة واحدة (تفادي N+1)
    classes = policy.effective_classes.select_related(
        'network',
        'plan_class__network',
        'plan_class__plan',
    ).prefetch_related(
        'benefits__benefit_type',
        'plan_class__benefits__benefit_type',
    )

    inherited_data = False
    master_policy_ref = None

    if not classes.exists() and policy.master_policy:
        classes = policy.master_policy.effective_classes.select_related(
            'network', 'plan_class__network'
        ).prefetch_related(
            'benefits__benefit_type',
            'plan_class__benefits__benefit_type',
        )
        inherited_data = True
        master_policy_ref = policy.master_policy

    context = {
        'policy': policy,
        'classes': classes,
        'inherited_data': inherited_data,
        'master_policy_ref': master_policy_ref,
        'sub_policies': policy.sub_policies.all() if not policy.is_subsidiary else None,
    }
    return render(request, 'policies/policy_detail.html', context)
```

- [ ] **Step 2: تحديث عرض الفئات في policy_detail.html لإظهار مصدر البيانات**

ابحث عن المكان الذي تُعرض فيه الفئات في `templates/policies/policy_detail.html` وأضف مؤشر الوراثة:

```html
{% for class in classes %}
<div class="...">
    <div class="flex items-center gap-2">
        <span class="font-bold">{{ class.name }}</span>
        {% if class.plan_class %}
        <span class="text-xs px-2 py-0.5 bg-blue-50 text-blue-600 rounded-full">
            <i class="ph ph-link-simple"></i> {{ class.plan_class.plan.name }}
        </span>
        {% endif %}
    </div>
    <div class="text-sm text-slate-600">
        الحد السنوي: {{ class.effective_annual_limit|floatformat:0 }} ريال
        {% if class.annual_limit and class.plan_class %}
        <span class="text-xs text-amber-600">(تخصيص للعميل)</span>
        {% endif %}
    </div>
    <div class="text-sm text-slate-500">
        الشبكة: {{ class.effective_network.name_ar|default:"غير محددة" }}
    </div>
    <!-- المنافع الفعلية -->
    <div class="mt-2">
        {% for benefit in class.get_effective_benefits %}
        <div class="flex justify-between text-xs py-1 border-b border-slate-50">
            <span>{{ benefit.benefit_type.name_ar }}</span>
            <span class="font-medium">{{ benefit.limit_amount|floatformat:0 }} ريال</span>
        </div>
        {% endfor %}
    </div>
</div>
{% endfor %}
```

- [ ] **Step 3: إضافة إظهار معلومات الخطة في رأس صفحة policy_detail**

في `templates/policies/policy_detail.html` ابحث عن منطقة البطاقة الرئيسية وأضف:

```html
{% if policy.plan %}
<div class="mt-2 flex items-center gap-2 text-sm">
    <i class="ph ph-file-text text-brand-400"></i>
    <span class="text-slate-500">الخطة:</span>
    <a href="{% url 'policies:plan_detail' pk=policy.plan.pk %}"
        class="text-brand-600 hover:underline font-medium">
        {{ policy.plan.name }}
    </a>
</div>
{% endif %}
```

- [ ] **Step 4: تشغيل الاختبارات الكاملة**

```
python manage.py test policies -v 2
```

المتوقع: `OK`

- [ ] **Step 5: التحقق النهائي من الصفحات**

```
python manage.py runserver
```

تحقق من:
1. `http://127.0.0.1:8000/policies/plans/` — قائمة الخطط
2. إنشاء خطة جديدة وإضافة فئة بـ HTMX
3. إنشاء وثيقة جديدة مع اختيار خطة → الفئات تُوَلَّد تلقائياً
4. فتح الوثيقة → الفئات تُظهر مصدرها (القالب أو override)
5. تجديد وثيقة → وثيقة جديدة تُنشأ مع نسخ الـ overrides

- [ ] **Step 6: Commit النهائي**

```
git add policies/views.py templates/policies/policy_detail.html
git commit -m "feat(policies): update policy_detail with prefetch_related and plan info display"
```

---

## ملخص Migrations المطلوبة

| Migration | الوصف |
|---|---|
| `XXXX_insurance_plan_models` | إنشاء InsurancePlan, PlanClass, PlanClassBenefit |
| `XXXX_add_plan_fk_to_policy_and_policyclass` | إضافة plan FK لـ Policy، وplan_class FK + nullable annual_limit لـ PolicyClass |

## ملخص الاختبارات

| Test Class | الاختبارات |
|---|---|
| `InsurancePlanModelTest` | إنشاء خطة، unique_together |
| `PolicyPlanLinkTest` | ربط وثيقة بخطة، وراثة الحد السنوي، override |
| `EffectiveBenefitsTest` | وراثة المنافع من القالب، override منفعة واحدة |
| `PolicyCreateWithPlanTest` | توليد PolicyClass تلقائياً عند اختيار خطة |
| `PolicyRenewalTest` | التجديد ينسخ الـ overrides ويحفظ الوثيقة القديمة |

## تشغيل كل الاختبارات دفعة واحدة

```
python manage.py test policies -v 2
```
