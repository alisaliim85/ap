from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Policy, PolicyClass, ClassBenefit, BenefitType
from .forms import PolicyForm, PolicyClassForm, ClassBenefitForm

# ==========================================
# 1. إدارة البوالص (Policies Management)
# ==========================================

@login_required
@permission_required('policies.view_policy', raise_exception=True)
def policy_list(request):
    """
    قائمة البوالص:
    - الوسيط: يرى كل البوالص.
    - مدير HR: يرى فقط البوالص المسجلة باسم شركته (ولا يرى بوليصة الشركة الأم هنا).
    """
    policies_list = Policy.objects.select_related('client', 'provider', 'master_policy').all().order_by('-created_at')

    # تصفية خاصة لمدير الموارد البشرية (HR)
    if request.user.has_perm('accounts.view_hr_dashboard') and not request.user.has_perm('accounts.view_broker_dashboard'):
        client = request.user.related_client
        if client:
            # ✅ عزل تام: يرى وثائقه الخاصة فقط
            policies_list = policies_list.filter(client=client)

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
    تفاصيل البوليصة:
    - تعرض بيانات البوليصة.
    - ✅ ميزة الوراثة: إذا كانت البوليصة تابعة (Subsidiary) ولا تملك فئات خاصة،
      يتم جلب وعرض فئات ومنافع البوليصة الأم تلقائياً.
    """
    policy = get_object_or_404(Policy.objects.select_related('client', 'provider', 'master_policy'), pk=pk)
    user = request.user
    
    # 1. حماية الوصول: التأكد من أن المستخدم يملك حق رؤية هذه الوثيقة
    if user.has_perm('accounts.view_hr_dashboard') and not user.has_perm('accounts.view_broker_dashboard'):
        client = user.related_client
        if policy.client != client:
             messages.error(request, "ليس لديك صلاحية الوصول لهذه الوثيقة")
             return redirect('policies:policy_list')

    # 2. منطق الوراثة (Inheritance Logic)
    # نحاول جلب الفئات الخاصة بهذه الوثيقة
    classes = policy.effective_classes.select_related('network')
    
    inherited_data = False
    master_policy_ref = None

    # إذا لم نجد فئات خاصة، وكانت هذه الوثيقة مرتبطة بوثيقة أم (Master Policy)
    # نقوم بعرض فئات الوثيقة الأم للمستخدم
    if not classes.exists() and policy.master_policy:
        classes = policy.master_policy.effective_classes.select_related('network')
        inherited_data = True
        master_policy_ref = policy.master_policy

    context = {
        'policy': policy, 
        'classes': classes,
        'inherited_data': inherited_data,        # متغير لإظهار تنبيه في HTML بأن هذه البيانات موروثة
        'master_policy_ref': master_policy_ref,  # مرجع للوثيقة الأم (للعرض فقط)
        'sub_policies': policy.sub_policies.all() if not policy.is_subsidiary else None,
    }
    return render(request, 'policies/policy_detail.html', context)


@login_required
@permission_required('policies.add_policy', raise_exception=True)
def policy_create(request):
    if request.method == 'POST':
        form = PolicyForm(request.POST, request.FILES)
        if form.is_valid():
            policy = form.save()
            messages.success(request, "تمت إضافة البوليصة بنجاح")
            return redirect('policies:policy_detail', pk=policy.pk)
    else:
        form = PolicyForm()
    return render(request, 'policies/policy_form.html', {'form': form, 'title': 'إضافة بوليصة جديدة'})


@login_required
@permission_required('policies.change_policy', raise_exception=True)
def policy_update(request, pk):
    policy = get_object_or_404(Policy, pk=pk)
    if request.method == 'POST':
        form = PolicyForm(request.POST, request.FILES, instance=policy)
        if form.is_valid():
            form.save()
            messages.success(request, "تم تحديث بيانات البوليصة بنجاح")
            return redirect('policies:policy_detail', pk=policy.pk)
    else:
        form = PolicyForm(instance=policy)
    return render(request, 'policies/policy_form.html', {'form': form, 'title': f'تعديل بوليصة: {policy.policy_number}', 'policy': policy})


@login_required
@permission_required('policies.delete_policy', raise_exception=True)
def policy_delete(request, pk):
    policy = get_object_or_404(Policy, pk=pk)
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
    policy = get_object_or_404(Policy, pk=policy_pk)
    if request.method == 'POST':
        form = PolicyClassForm(request.POST)
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
@permission_required('policies.view_policy', raise_exception=True) # ✅ السماح بالعرض (View)
def class_benefit_manage(request, class_pk):
    """
    صفحة عرض وإدارة المنافع.
    - HR: يشاهد المنافع فقط (سواء كانت لشركته أو الموروثة من الأم).
    - Broker: يشاهد ويعدل.
    """
    policy_class = get_object_or_404(PolicyClass, pk=class_pk)
    policy = policy_class.policy # الوثيقة التي تملك هذا الكلاس (قد تكون الأم)
    user = request.user

    # 1. التحقق من الصلاحية الهرمية (Hierarchical Check)
    # يجب السماح للمستخدم بالدخول إذا كان الكلاس يتبع وثيقته، أو يتبع وثيقة الشركة الأم
    if user.has_perm('accounts.view_hr_dashboard') and not user.has_perm('accounts.view_broker_dashboard'):
        client = user.related_client
        
        is_own_policy = (policy.client == client)
        is_parent_policy = (client.parent and policy.client == client.parent)
        
        if not (is_own_policy or is_parent_policy):
             messages.error(request, "لا تملك صلاحية عرض هذه المنافع")
             return redirect('policies:policy_list')

    # 2. إعداد البيانات
    benefits = policy_class.benefits.all().select_related('benefit_type')
    benefit_types = BenefitType.objects.all()
    is_broker = user.has_perm('policies.change_policy') # لتحديد ظهور أزرار التعديل

    # 3. معالجة الحفظ (POST Request) - للوسطاء فقط
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
        'is_broker': is_broker, # متغير مهم للقالب
    })


@login_required
@permission_required('policies.view_policy', raise_exception=True)
def benefit_type_list(request):
    types = BenefitType.objects.all()
    return render(request, 'policies/benefit_type_list.html', {'types': types})