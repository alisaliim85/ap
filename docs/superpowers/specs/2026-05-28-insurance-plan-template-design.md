# Insurance Plan Template — Design Spec
**Date:** 2026-05-28  
**Status:** Approved for Implementation

---

## 1. المشكلة (Problem Statement)

الوسيط يُعيد إدخال نفس تفاصيل الوثيقة (فئات تأمينية + منافع + حدود تغطية) لكل عميل جديد يشتري منتجاً مشابهاً من نفس شركة التأمين. هذا يؤدي إلى:

- **تكرار بيانات** كثير عبر الوثائق.
- **عدم اتساق** عند التحديث (يجب تعديل كل وثيقة يدوياً).
- **بطء في الإعداد** — إنشاء وثيقة جديدة يستغرق وقتاً طويلاً.
- **صعوبة التجديد** — لا توجد آلية منظمة لتجديد الوثيقة مع تغيير جزئي.

---

## 2. السياق الحالي (Current Architecture)

```
Broker → Client → Policy → PolicyClass → ClassBenefit
                                       → Network → ServiceProvider
Provider → Network
BenefitType (master data — global)
ServiceProvider (master data — global)
```

**النقاط الجيدة الموجودة:**
- `ServiceProvider` عالمي — المستشفى يُدخَل مرة واحدة ويُشارَك بين كل الشبكات.
- `Network` مرتبط بـ Provider — الشبكات مُعرَّفة عند شركة التأمين وليس عند كل عميل.
- `Policy.save()` يُطبِّق Denormalization للأداء.

**الفجوة:**
لا يوجد مفهوم "المنتج التأميني" (Insurance Plan) كقالب يُعرَّف مرة واحدة لكل شركة تأمين ثم تستخدمه الوثائق المتعددة.

---

## 3. القرار المعماري — Insurance Plan Template Layer

### المبدأ الأساسي
**فصل تعريف المنتج التأميني عن تفاصيل عقد العميل.**

```
Provider (شركة التأمين)
  └─► InsurancePlan (المنتج: "بوبا الذهبي 2026") ← يُعرَّف مرة واحدة لكل وسيط
       ├─► PlanClass (VIP, فئة أ, فئة ج ...) ← مسميات شركة التأمين
       │    ├─ network FK → Network (الشبكة الافتراضية)
       │    ├─ annual_limit (الحد السنوي الافتراضي)
       │    └─► PlanClassBenefit (أسنان: 5000, بصريات: 2000 ...)
       │
Policy (وثيقة العميل) → plan FK → InsurancePlan
  └─► PolicyClass → plan_class FK → PlanClass  (nullable — backward compatible)
       ├─ network (null = يرث | مضبوط = override)
       ├─ annual_limit (null = يرث | مضبوط = override)
       └─► ClassBenefit (override اختياري لمنفعة معينة فقط)
```

---

## 4. النماذج الجديدة (New Models — policies/models.py)

### 4.1 InsurancePlan

```python
class InsurancePlan(models.Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    broker = FK('brokers.Broker', on_delete=CASCADE, related_name='insurance_plans')
    provider = FK('providers.Provider', on_delete=PROTECT, related_name='plans')
    name = CharField(max_length=150)          # "بوبا الذهبي 2026"
    description = TextField(blank=True)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('broker', 'provider', 'name')
```

**عزل البيانات:** `broker` FK يضمن أن كل وسيط يرى خططه فقط.

### 4.2 PlanClass

```python
class PlanClass(models.Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = FK(InsurancePlan, on_delete=CASCADE, related_name='classes')
    name = CharField(max_length=50)           # "VIP", "فئة أ", "بلاتينيوم"
    network = FK('networks.Network', on_delete=SET_NULL, null=True, blank=True)
    annual_limit = DecimalField(max_digits=12, decimal_places=2)
    order = PositiveSmallIntegerField(default=0)  # لترتيب العرض

    class Meta:
        unique_together = ('plan', 'name')
        ordering = ['order']
```

### 4.3 PlanClassBenefit

```python
class PlanClassBenefit(models.Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan_class = FK(PlanClass, on_delete=CASCADE, related_name='benefits')
    benefit_type = FK('policies.BenefitType', on_delete=PROTECT)
    limit_amount = DecimalField(max_digits=10, decimal_places=2, default=0)
    deductible_percentage = IntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    description = TextField(blank=True)

    class Meta:
        unique_together = ('plan_class', 'benefit_type')
```

---

## 5. التعديلات على النماذج الحالية (Backward Compatible)

### 5.1 Policy — إضافة FK واحد

```python
# حقل جديد — nullable لضمان توافق البيانات القديمة
plan = FK(
    InsurancePlan,
    on_delete=SET_NULL,
    null=True, blank=True,
    related_name='policies'
)
```

**البيانات القديمة:** `plan = null` → تعمل كما هي دون أي تغيير.

### 5.2 PolicyClass — إضافة FK واحد + تعديل annual_limit

```python
# حقل جديد — nullable
plan_class = FK(
    PlanClass,
    on_delete=SET_NULL,
    null=True, blank=True,
    related_name='policy_classes'
)

# تعديل مطلوب على الحقل الحالي: جعل annual_limit nullable
# (migration آمنة — لا تمس البيانات القديمة، فقط تُضيف NULL كخيار)
annual_limit = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
# عندما plan_class مضبوط: null = يرث من PlanClass | مضبوط = override لهذا العميل
# عندما plan_class = null: تعمل كحقل عادي إلزامي (السلوك القديم)

# network موجود بالفعل كـ nullable — لا تغيير مطلوب
```

**تحذير:** دالة `clean()` الحالية في PolicyClass تتحقق أن الشبكة تتبع نفس مزود الوثيقة.
يجب تحديثها لتتحقق من `effective_network` بدلاً من `self.network` مباشرة:

```python
def clean(self):
    effective_net = self.effective_network  # يحسب الشبكة الفعلية (override أو inherited)
    if effective_net and self.policy_id:
        effective_provider = self.policy.effective_provider
        if effective_provider and effective_net.provider_id != effective_provider.pk:
            raise ValidationError(...)
```

---

## 6. منطق الوراثة (Inheritance Logic)

### 6.1 خصائص effective_ على PolicyClass

```python
@property
def effective_network(self):
    """الشبكة الفعلية: override الوثيقة أولاً، ثم القالب."""
    if self.network_id:
        return self.network
    if self.plan_class_id:
        return self.plan_class.network
    return None

@property
def effective_annual_limit(self):
    """الحد السنوي الفعلي."""
    if self.annual_limit is not None:
        return self.annual_limit
    if self.plan_class_id:
        return self.plan_class.annual_limit
    return None
```

### 6.2 دالة get_effective_benefits — مع تفادي N+1

```python
def get_effective_benefits(self):
    """
    يُرجع قائمة المنافع الفعلية مع تفادي N+1.
    الأولوية: ClassBenefit (override) → PlanClassBenefit (افتراضي)

    يُفترض استدعاء هذه الدالة بعد prefetch_related كالتالي:
        PolicyClass.objects.prefetch_related(
            'benefits__benefit_type',
            'plan_class__benefits__benefit_type'
        )
    """
    # overrides محفوظة في dict بـ benefit_type_id
    overrides = {b.benefit_type_id: b for b in self.benefits.all()}

    if not self.plan_class_id:
        return list(self.benefits.all())

    result = []
    seen_ids = set()

    for pb in self.plan_class.benefits.all():
        seen_ids.add(pb.benefit_type_id)
        if pb.benefit_type_id in overrides:
            result.append(overrides[pb.benefit_type_id])  # override يسبق القالب
        else:
            result.append(pb)  # يرث من القالب

    # أي منافع override إضافية غير موجودة في القالب
    for b in self.benefits.all():
        if b.benefit_type_id not in seen_ids:
            result.append(b)

    return result
```

### 6.3 قاعدة الاستخدام الإلزامية لتفادي N+1

**في كل view أو service يستخدم effective_benefits أو effective_network:**

```python
# ✅ الطريقة الصحيحة دائماً
PolicyClass.objects.select_related(
    'network',
    'plan_class__network',
    'plan_class__plan__provider',
).prefetch_related(
    'benefits__benefit_type',
    'plan_class__benefits__benefit_type',
)

# ✅ لعرض الأعضاء مع بياناتهم الكاملة
Member.objects.select_related(
    'policy_class__network',
    'policy_class__plan_class__network',
    'policy_class__plan_class',
).prefetch_related(
    'policy_class__benefits__benefit_type',
    'policy_class__plan_class__benefits__benefit_type',
    'policy_class__network__hospitals',
)
```

---

## 7. عزل البيانات (Data Isolation — Multi-Tenancy)

### 7.1 دالة get_allowed_plans

```python
def get_allowed_plans(user):
    """
    عزل InsurancePlan بحسب دور المستخدم.
    InsurancePlan مملوك للوسيط — HR والأعضاء لا يرونه مباشرة.
    """
    if user.role == User.Roles.SUPER_ADMIN:
        return InsurancePlan.objects.all()
    elif user.is_broker_role and user.related_broker:
        return InsurancePlan.objects.filter(broker=user.related_broker)
    return InsurancePlan.objects.none()
```

### 7.2 صلاحيات كل دور

| الدور | InsurancePlan | PolicyClass (عرض) | مستشفيات الشبكة |
|---|---|---|---|
| `SUPER_ADMIN` | إدارة كاملة | إدارة كاملة | إدارة كاملة |
| `BROKER_ADMIN/STAFF` | إدارة خططه فقط | وثائق عملائه فقط | عرض فقط |
| `HR_ADMIN/STAFF` | ❌ | وثيقة شركته فقط | عرض مستشفيات وثيقتهم |
| `MEMBER` | ❌ | فئته فقط | مستشفيات فئته فقط |

---

## 8. سير العمل (Workflows)

### 8.1 الوسيط يُعرِّف منتجاً جديداً (مرة واحدة)

```
1. الوسيط → "خطط التأمين" → "إضافة خطة"
2. يختار شركة التأمين (Provider)
3. يسمي الخطة: "بوبا الذهبي 2026"
4. يُضيف فئات (PlanClass): VIP, فئة أ, فئة ج
5. لكل فئة: يختار الشبكة + الحد السنوي + المنافع
6. يحفظ → الخطة جاهزة للاستخدام في أي وثيقة
```

### 8.2 إنشاء وثيقة جديدة لعميل

```
1. الوسيط → "وثائق" → "وثيقة جديدة"
2. يختار العميل + شركة التأمين + الخطة
3. النظام يُنشئ PolicyClass تلقائياً لكل PlanClass في الخطة
   (plan_class مضبوط، network=null → يرث)
4. الوسيط يُعدِّل فقط ما يختلف لهذا العميل (override)
```

### 8.3 تجديد وثيقة منتهية

```
1. الوسيط → الوثيقة القديمة → "تجديد"
2. النظام يُنشئ Policy جديدة (تواريخ جديدة، نفس الخطة)
3. ينسخ PolicyClass + overrides من الوثيقة القديمة
4. الوسيط يُعدِّل ما تغيّر فقط (شبكة جديدة، حد جديد لفئة معينة)
5. الوثيقة القديمة تبقى محفوظة كسجل تاريخي
```

### 8.4 إضافة الأعضاء (HR أو الوسيط بالنيابة)

```
1. HR/وسيط → "الأعضاء" → رفع Excel أو إضافة يدوية
2. كل عضو: الاسم + الهوية + الوثيقة + الفئة (PolicyClass)
3. المنسوبون: مرتبطون بالموظف الأساسي (sponsor FK)
4. كل عضو يرث مستشفياته وفئته من PolicyClass تلقائياً
```

---

## 9. واجهات المستخدم المطلوبة (UI Scope)

### للوسيط

| الصفحة | الوصف |
|---|---|
| `plans/` | قائمة خطط التأمين مع البحث والفلترة |
| `plans/create/` | إنشاء خطة جديدة مع HTMX لإضافة الفئات ديناميكياً |
| `plans/<id>/` | تفاصيل خطة: الفئات + المنافع + الوثائق المرتبطة |
| `plans/<id>/classes/<cid>/` | تعديل فئة وإدارة منافعها |
| تعديل `policies/create/` | إضافة حقل اختيار الخطة + توليد الفئات تلقائياً |
| تعديل `policies/<id>/` | إضافة زر "تجديد" + عرض الـ overrides |

### للعضو

| الصفحة | الوصف |
|---|---|
| بطاقة الوثيقة | عرض المنافع الفعلية (effective_benefits) |
| قائمة المستشفيات | عرض effective_network.hospitals مع فلتر المدينة |

---

## 10. ما هو خارج النطاق (Out of Scope)

- ❌ مزامنة مع API شركات التأمين
- ❌ Versioning للخطط (التجديد يُعالَج بوثيقة جديدة)
- ❌ موافقة العضو الإلكترونية على شروط الوثيقة
- ❌ مقارنة بين خطتين
- ❌ استيراد خطة من ملف Excel (ممكن لاحقاً)

---

## 11. اعتبارات الأداء (Performance)

| الاعتبار | الحل المُطبَّق |
|---|---|
| N+1 في effective_benefits | `prefetch_related('benefits', 'plan_class__benefits')` إلزامي |
| N+1 في effective_network | `select_related('network', 'plan_class__network')` إلزامي |
| حجم قوائم المستشفيات | Pagination في عرض الشبكة |
| استعلامات عزل البيانات | Index على `broker_id` في InsurancePlan |
| توسع مستقبلي | Denormalization للـ effective_network_id إذا لزم لاحقاً |

---

## 12. مسار التنفيذ المقترح

```
الخطوة 1: النماذج الجديدة + migration
           (InsurancePlan, PlanClass, PlanClassBenefit)
           + حقلا plan + plan_class على Policy و PolicyClass

الخطوة 2: خصائص الوراثة على PolicyClass
           (effective_network, effective_annual_limit, get_effective_benefits)

الخطوة 3: Admin للتحقق السريع من البيانات

الخطوة 4: واجهة "خطط التأمين" للوسيط (CRUD كامل)

الخطوة 5: تعديل واجهة "إنشاء وثيقة" لاستخدام الخطة
           + توليد PolicyClass تلقائياً عبر HTMX

الخطوة 6: زر "تجديد وثيقة" مع نسخ الـ overrides

الخطوة 7: تحديث عرض العضو (effective_benefits + effective_network)
           مع ضمان select_related/prefetch_related في كل view
```
