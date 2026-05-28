from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Policy, PolicyClass, ClassBenefit, BenefitType, InsurancePlan, PlanClass, PlanClassBenefit
from .forms import PolicyForm, PolicyClassForm, ClassBenefitForm
from accounts.models import User

# ==========================================
# دالة مساعدة: عزل البيانات للوسطاء والعملاء (Data Isolation)
# ==========================================
def get_allowed_policies(user):
    """
    تُرجع البوالص المسموح للمستخدم رؤيتها/إدارتها بناءً على دوره.
    """
    # 1. السوبر أدمن يرى كل البوالص
    if user.role == User.Roles.SUPER_ADMIN:
        return Policy.objects.all()
        
    # 2. الوسيط يرى بوالص العملاء التابعين لشركته فقط
    elif user.is_broker_role and user.related_broker:
        return Policy.objects.filter(client__broker=user.related_broker)
        
    # 3. مدير الموارد البشرية (HR) يرى بوالص شركته فقط
    elif user.is_hr_role and user.related_client:
        return Policy.objects.filter(client=user.related_client)
        
    return Policy.objects.none()


def get_allowed_plans(user):
    """
    تُرجع InsurancePlan المسموح للمستخدم رؤيتها.
    الخطط مملوكة للوسيط — HR والأعضاء لا يصلون إليها مباشرة.
    """
    if user.role == User.Roles.SUPER_ADMIN:
        return InsurancePlan.objects.all()
    elif user.is_broker_role and user.related_broker:
        return InsurancePlan.objects.filter(broker=user.related_broker)
    return InsurancePlan.objects.none()


# ==========================================
# 1. إدارة البوالص (Policies Management)
# ==========================================

@login_required
@permission_required('policies.view_policy', raise_exception=True)
def policy_list(request):
    """
    قائمة البوالص - [تم تطبيق عزل الـ SaaS]
    """
    # استخدام الدالة المساعدة لجلب البوالص المصرح بها فقط
    policies_list = get_allowed_policies(request.user).select_related('client', 'provider', 'master_policy').order_by('-created_at')

    # منطق البحث
    search_query = request.GET.get('search', '')
    if search_query:
        policies_list = policies_list.filter(
            Q(policy_number__icontains=search_query) |
            Q(client__name_ar__icontains=search_query) |
            Q(client__name_en__icontains=search_query)
        )

    # الترقيم (Pagination)
    paginator = Paginator(policies_list, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    if request.headers.get('HX-Request'):
        return render(request, 'policies/partials/policy_table.html', {'policies': page_obj})

    return render(request, 'policies/policy_list.html', {'policies': page_obj})


@login_required
@permission_required('policies.view_policy', raise_exception=True)
def policy_detail(request, pk):
    """
    تفاصيل البوليصة مع N+1 prevention كامل.
    """
    policy = get_object_or_404(
        get_allowed_policies(request.user).select_related(
            'client', 'provider', 'master_policy', 'plan__provider'
        ),
        pk=pk,
    )

    # جلب الفئات مع كل بياناتها بـ query واحد فعال
    classes_qs = policy.effective_classes.select_related(
        'network',
        'plan_class__network',
        'plan_class__plan__provider',
    ).prefetch_related(
        'benefits__benefit_type',
        'plan_class__benefits__benefit_type',
    )

    inherited_data = False
    master_policy_ref = None
    if not classes_qs.exists() and policy.master_policy:
        classes_qs = policy.master_policy.effective_classes.select_related(
            'network', 'plan_class__network',
        ).prefetch_related(
            'benefits__benefit_type',
            'plan_class__benefits__benefit_type',
        )
        inherited_data = True
        master_policy_ref = policy.master_policy

    context = {
        'policy': policy,
        'classes': classes_qs,
        'inherited_data': inherited_data,
        'master_policy_ref': master_policy_ref,
        'sub_policies': policy.sub_policies.all() if not policy.is_subsidiary else None,
    }
    return render(request, 'policies/policy_detail.html', context)


@login_required
@permission_required('policies.add_policy', raise_exception=True)
def policy_create(request):
    if request.method == 'POST':
        form = PolicyForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            policy = form.save()
            # توليد PolicyClass تلقائياً من PlanClass إذا اختار الوسيط خطة
            if policy.plan_id:
                plan_classes = policy.plan.classes.prefetch_related('benefits').order_by('order', 'name')
                for plan_cls in plan_classes:
                    PolicyClass.objects.create(
                        policy=policy,
                        plan_class=plan_cls,
                        name=plan_cls.name,
                        # network=None → يرث من plan_class عبر effective_network
                        # annual_limit=None → يرث من plan_class عبر effective_annual_limit
                    )
            messages.success(request, "تمت إضافة البوليصة بنجاح")
            return redirect('policies:policy_detail', pk=policy.pk)
    else:
        form = PolicyForm(user=request.user)
    return render(request, 'policies/policy_form.html', {'form': form, 'title': 'إضافة بوليصة جديدة'})


@login_required
@permission_required('policies.change_policy', raise_exception=True)
def policy_update(request, pk):
    # التأكد أن الوسيط يعدل بوليصة تابعة له فقط
    policy = get_object_or_404(get_allowed_policies(request.user), pk=pk)
    
    if request.method == 'POST':
        form = PolicyForm(request.POST, request.FILES, instance=policy, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "تم تحديث بيانات البوليصة بنجاح")
            return redirect('policies:policy_detail', pk=policy.pk)
    else:
        form = PolicyForm(instance=policy, user=request.user)
    return render(request, 'policies/policy_form.html', {'form': form, 'title': f'تعديل بوليصة: {policy.policy_number}', 'policy': policy})


@login_required
@permission_required('policies.delete_policy', raise_exception=True)
def policy_delete(request, pk):
    policy = get_object_or_404(get_allowed_policies(request.user), pk=pk)
    if request.method == 'POST':
        # حذف لين: في أنظمة التأمين لا تُحذف الوثيقة أبداً حفاظاً على سجل المطالبات التاريخية
        num = policy.policy_number
        policy.is_active = False
        policy.save(update_fields=['is_active'])
        messages.success(request, f"تم إلغاء تفعيل البوليصة رقم {num} بنجاح")
        return redirect('policies:policy_list')
    return render(request, 'policies/policy_confirm_delete.html', {'policy': policy})


@login_required
@permission_required('policies.add_policy', raise_exception=True)
def policy_renew(request, pk):
    """
    تجديد وثيقة منتهية: ينشئ وثيقة جديدة بنفس الخطة وينسخ overrides من الوثيقة القديمة.
    """
    old_policy = get_object_or_404(get_allowed_policies(request.user).select_related('plan', 'provider', 'client'), pk=pk)

    if request.method == 'POST':
        new_start = request.POST.get('start_date')
        new_end = request.POST.get('end_date')
        new_number = request.POST.get('policy_number', '').strip()

        if not new_start or not new_end or not new_number:
            messages.error(request, "يرجى تعبئة جميع الحقول المطلوبة.")
            return render(request, 'policies/policy_renew_confirm.html', {'old_policy': old_policy})

        # إنشاء الوثيقة الجديدة بنسخ بيانات القديمة
        new_policy = Policy.objects.create(
            client=old_policy.client,
            provider=old_policy.provider,
            plan=old_policy.plan,
            master_policy=old_policy.master_policy,
            policy_number=new_number,
            start_date=new_start,
            end_date=new_end,
            is_active=True,
        )

        # نسخ PolicyClass + overrides من الوثيقة القديمة
        old_classes = old_policy.classes.select_related('plan_class', 'network').prefetch_related('benefits__benefit_type')
        for old_cls in old_classes:
            new_cls = PolicyClass.objects.create(
                policy=new_policy,
                plan_class=old_cls.plan_class,
                name=old_cls.name,
                network=old_cls.network,           # نسخ override الشبكة
                annual_limit=old_cls.annual_limit,  # نسخ override الحد السنوي
            )
            # نسخ ClassBenefit overrides
            for benefit in old_cls.benefits.all():
                ClassBenefit.objects.create(
                    policy_class=new_cls,
                    benefit_type=benefit.benefit_type,
                    limit_amount=benefit.limit_amount,
                    deductible_percentage=benefit.deductible_percentage,
                    description=benefit.description,
                )

        # تعطيل الوثيقة القديمة (اختياري — يمكن تركها نشطة كسجل تاريخي)
        # old_policy.is_active = False
        # old_policy.save(update_fields=['is_active'])

        messages.success(request, f"تم تجديد الوثيقة بنجاح. الرقم الجديد: {new_policy.policy_number}")
        return redirect('policies:policy_detail', pk=new_policy.pk)

    return render(request, 'policies/policy_renew_confirm.html', {'old_policy': old_policy})


# ==========================================
# 2. إدارة الفئات والمنافع (Classes & Benefits)
# ==========================================

@login_required
@permission_required('policies.change_policy', raise_exception=True)
def policy_class_create(request, policy_pk):
    # حماية: التأكد أن البوليصة التي نضيف لها كلاس تابعة لوسيط المستخدم
    policy = get_object_or_404(get_allowed_policies(request.user), pk=policy_pk)
    
    if request.method == 'POST':
        form = PolicyClassForm(request.POST) # لا حاجة لتمرير user هنا ما لم يكن هناك قوائم منسدلة تحتاج فلترة
        if form.is_valid():
            policy_class = form.save(commit=False)
            policy_class.policy = policy
            policy_class.save()
            messages.success(request, f"تمت إضافة الفئة {policy_class.name} بنجاح")
            return redirect('policies:policy_detail', pk=policy.pk)
    else:
        form = PolicyClassForm()
    return render(request, 'policies/class_form.html', {'form': form, 'policy': policy, 'title': 'إضافة فئة جديدة'})


@login_required
@permission_required('policies.view_policy', raise_exception=True)
def class_benefit_manage(request, class_pk):
    """
    صفحة عرض وإدارة المنافع - [تم تطبيق حماية الـ SaaS]
    """
    policy_class = get_object_or_404(PolicyClass, pk=class_pk)
    policy = policy_class.policy
    user = request.user

    # 1. التحقق من الصلاحية (هل المستخدم وسيط يملك البوليصة؟ أو HR يتبع لشركتها؟)
    if user.role == User.Roles.SUPER_ADMIN:
        has_access = True
    elif user.is_broker_role and user.related_broker:
        has_access = (policy.client.broker == user.related_broker)
    elif user.is_hr_role and user.related_client:
        client = user.related_client
        has_access = (policy.client == client) or (client.parent and policy.client == client.parent)
    else:
        has_access = False

    if not has_access:
        messages.error(request, "لا تملك صلاحية عرض هذه المنافع")
        return redirect('policies:policy_list')

    # 2. إعداد البيانات
    benefits = policy_class.benefits.all().select_related('benefit_type')
    benefit_types = BenefitType.objects.all()
    # يُسمح بالتعديل للسوبر أدمن وموظفي الوسيط فقط
    is_broker = user.role == User.Roles.SUPER_ADMIN or user.is_broker_role 

    # 3. معالجة الحفظ (POST Request)
    if request.method == 'POST':
        if not is_broker:
            messages.error(request, "عذراً، لديك صلاحية العرض فقط")
            return redirect('policies:class_benefit_manage', class_pk=policy_class.pk)

        benefit_id = request.POST.get('benefit_id')
        if benefit_id:
            benefit = get_object_or_404(ClassBenefit, pk=benefit_id)
            form = ClassBenefitForm(request.POST, instance=benefit)
        else:
            form = ClassBenefitForm(request.POST)
        
        if form.is_valid():
            benefit = form.save(commit=False)
            benefit.policy_class = policy_class
            benefit.save()
            messages.success(request, "تم حفظ بيانات المنفعة بنجاح")
            return redirect('policies:class_benefit_manage', class_pk=policy_class.pk)

    return render(request, 'policies/benefit_manage.html', {
        'policy_class': policy_class,
        'benefits': benefits,
        'benefit_types': benefit_types,
        'is_broker': is_broker,
    })


@login_required
@permission_required('policies.view_policy', raise_exception=True)
def benefit_type_list(request):
    # قائمة أنواع المنافع عامة (Master Data)، لذا لا تتطلب فلترة بالوسيط
    types = BenefitType.objects.all()
    return render(request, 'policies/benefit_type_list.html', {'types': types})


# ==========================================
# إدارة خطط التأمين (Insurance Plan Templates)
# ==========================================

@login_required
@permission_required('policies.manage_insurance_plans', raise_exception=True)
def plan_list(request):
    """قائمة خطط التأمين مع البحث والفلترة."""
    plans_qs = get_allowed_plans(request.user).select_related('broker', 'provider')

    search_query = request.GET.get('search', '')
    if search_query:
        plans_qs = plans_qs.filter(
            Q(name__icontains=search_query) | Q(provider__name_en__icontains=search_query)
        )

    provider_filter = request.GET.get('provider', '')
    if provider_filter:
        plans_qs = plans_qs.filter(provider_id=provider_filter)

    paginator = Paginator(plans_qs, 20)
    page = request.GET.get('page')
    plans = paginator.get_page(page)

    from providers.models import Provider
    providers = Provider.objects.all().order_by('name_en')

    return render(request, 'policies/plan_list.html', {
        'plans': plans,
        'search_query': search_query,
        'provider_filter': provider_filter,
        'providers': providers,
    })


@login_required
@permission_required('policies.manage_insurance_plans', raise_exception=True)
def plan_create(request):
    """إنشاء خطة تأمين جديدة."""
    from .forms import InsurancePlanForm
    if request.method == 'POST':
        form = InsurancePlanForm(request.POST, user=request.user)
        if form.is_valid():
            plan = form.save(commit=False)
            if request.user.is_broker_role and request.user.related_broker:
                plan.broker = request.user.related_broker
            plan.save()
            messages.success(request, f"تم إنشاء الخطة '{plan.name}' بنجاح.")
            return redirect('policies:plan_detail', plan_pk=plan.pk)
    else:
        form = InsurancePlanForm(user=request.user)
    return render(request, 'policies/plan_form.html', {'form': form, 'title': 'إنشاء خطة تأمين جديدة'})


@login_required
@permission_required('policies.manage_insurance_plans', raise_exception=True)
def plan_detail(request, plan_pk):
    """تفاصيل الخطة: الفئات + المنافع + الوثائق المرتبطة."""
    plan = get_object_or_404(
        get_allowed_plans(request.user).select_related('broker', 'provider'),
        pk=plan_pk,
    )
    classes = plan.classes.select_related('network').prefetch_related('benefits__benefit_type').order_by('order', 'name')
    linked_policies_count = plan.policies.filter(is_active=True).count()
    return render(request, 'policies/plan_detail.html', {
        'plan': plan,
        'classes': classes,
        'linked_policies_count': linked_policies_count,
    })


@login_required
@permission_required('policies.manage_insurance_plans', raise_exception=True)
def plan_update(request, plan_pk):
    """تعديل بيانات الخطة الأساسية."""
    plan = get_object_or_404(get_allowed_plans(request.user), pk=plan_pk)
    from .forms import InsurancePlanForm
    if request.method == 'POST':
        form = InsurancePlanForm(request.POST, instance=plan, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "تم تحديث الخطة بنجاح.")
            return redirect('policies:plan_detail', plan_pk=plan.pk)
    else:
        form = InsurancePlanForm(instance=plan, user=request.user)
    return render(request, 'policies/plan_form.html', {'form': form, 'plan': plan, 'title': 'تعديل الخطة'})


@login_required
@permission_required('policies.manage_insurance_plans', raise_exception=True)
def plan_class_create(request, plan_pk):
    """إضافة فئة جديدة لخطة تأمين."""
    plan = get_object_or_404(get_allowed_plans(request.user), pk=plan_pk)
    from .forms import PlanClassForm
    if request.method == 'POST':
        form = PlanClassForm(request.POST, plan=plan)
        if form.is_valid():
            plan_class = form.save(commit=False)
            plan_class.plan = plan
            plan_class.save()
            if request.htmx:
                classes = plan.classes.select_related('network').prefetch_related('benefits__benefit_type').order_by('order', 'name')
                return render(request, 'policies/partials/plan_classes_list.html', {'plan': plan, 'classes': classes})
            messages.success(request, f"تم إضافة الفئة '{plan_class.name}' بنجاح.")
            return redirect('policies:plan_detail', plan_pk=plan.pk)
    else:
        form = PlanClassForm(plan=plan)
    return render(request, 'policies/partials/plan_class_form.html', {'form': form, 'plan': plan})


@login_required
@permission_required('policies.manage_insurance_plans', raise_exception=True)
def plan_class_benefit_manage(request, plan_pk, class_pk):
    """إدارة منافع فئة خطة التأمين."""
    plan = get_object_or_404(get_allowed_plans(request.user), pk=plan_pk)
    plan_class = get_object_or_404(PlanClass, pk=class_pk, plan=plan)
    benefits = plan_class.benefits.select_related('benefit_type').all()
    benefit_types = BenefitType.objects.all().order_by('name_en')
    from .forms import PlanClassBenefitForm

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'delete':
            benefit_id = request.POST.get('benefit_id')
            PlanClassBenefit.objects.filter(pk=benefit_id, plan_class=plan_class).delete()
            messages.success(request, "تم حذف المنفعة بنجاح.")
            return redirect('policies:plan_class_benefit_manage', plan_pk=plan.pk, class_pk=plan_class.pk)

        benefit_id = request.POST.get('benefit_id')
        if benefit_id:
            benefit = get_object_or_404(PlanClassBenefit, pk=benefit_id, plan_class=plan_class)
            form = PlanClassBenefitForm(request.POST, instance=benefit)
        else:
            form = PlanClassBenefitForm(request.POST)
        if form.is_valid():
            benefit = form.save(commit=False)
            benefit.plan_class = plan_class
            benefit.save()
            messages.success(request, "تم حفظ بيانات المنفعة بنجاح.")
            return redirect('policies:plan_class_benefit_manage', plan_pk=plan.pk, class_pk=plan_class.pk)
    else:
        form = PlanClassBenefitForm()

    return render(request, 'policies/plan_class_benefit_manage.html', {
        'plan': plan,
        'plan_class': plan_class,
        'benefits': benefits,
        'benefit_types': benefit_types,
        'form': form,
    })


@login_required
@permission_required('policies.manage_insurance_plans', raise_exception=True)
def plan_get_classes(request, plan_pk):
    """HTMX endpoint: يُرجع خيارات الفئات لخطة معينة لحقل select."""
    plan = get_object_or_404(get_allowed_plans(request.user), pk=plan_pk)
    classes = plan.classes.order_by('order', 'name')
    return render(request, 'policies/partials/plan_classes_options.html', {'classes': classes})