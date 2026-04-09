from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Policy, PolicyClass, ClassBenefit, BenefitType
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
    تفاصيل البوليصة - [محمية بالكامل ضد الاختراق بين الوسطاء]
    """
    # بمجرد استخدام get_allowed_policies، نضمن أن الوسيط (أو الـ HR) لا يمكنه فتح بوليصة لا تخصه
    # ولذلك تم الاستغناء عن شروط التحقق اليدوية السابقة!
    policy = get_object_or_404(get_allowed_policies(request.user).select_related('client', 'provider', 'master_policy'), pk=pk)
    
    # منطق الوراثة (Inheritance Logic)
    classes = policy.effective_classes.select_related('network')
    
    inherited_data = False
    master_policy_ref = None

    if not classes.exists() and policy.master_policy:
        classes = policy.master_policy.effective_classes.select_related('network')
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


@login_required
@permission_required('policies.add_policy', raise_exception=True)
def policy_create(request):
    if request.method == 'POST':
        # تمرير المستخدم للفورم لفلترة قائمة العملاء المنسدلة (سنعدل الـ Form لاحقاً)
        form = PolicyForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            policy = form.save()
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
        num = policy.policy_number
        policy.delete()
        messages.success(request, f"تم حذف البوليصة رقم {num} بنجاح")
        return redirect('policies:policy_list')
    return render(request, 'policies/policy_confirm_delete.html', {'policy': policy})


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