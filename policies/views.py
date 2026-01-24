from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Policy, PolicyClass, ClassBenefit, BenefitType
from .forms import PolicyForm, PolicyClassForm, ClassBenefitForm

@login_required
def policy_list(request):
    """
    عرض قائمة بوالص التأمين
    """
    if not request.user.is_broker:
        messages.error(request, "ليس لديك صلاحية الوصول لهذه الصفحة")
        return redirect('dashboard')

    policies_list = Policy.objects.all().order_by('-created_at')

    # البحث
    search_query = request.GET.get('search', '')
    if search_query:
        policies_list = policies_list.filter(
            Q(policy_number__icontains=search_query) |
            Q(client__name_ar__icontains=search_query) |
            Q(client__name_en__icontains=search_query) |
            Q(provider__name_ar__icontains=search_query)
        )

    # الترقيم
    paginator = Paginator(policies_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.headers.get('HX-Request'):
        return render(request, 'policies/partials/policy_table.html', {'policies': page_obj, 'page_obj': page_obj})

    return render(request, 'policies/policy_list.html', {'policies': page_obj, 'page_obj': page_obj})

@login_required
def policy_create(request):
    if not request.user.is_broker:
        messages.error(request, "ليس لديك صلاحية الوصول لهذه الصفحة")
        return redirect('dashboard')

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
def policy_update(request, pk):
    policy = get_object_or_404(Policy, pk=pk)
    if not request.user.is_broker:
        messages.error(request, "ليس لديك صلاحية الوصول لهذه الصفحة")
        return redirect('dashboard')

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
def policy_detail(request, pk):
    policy = get_object_or_404(Policy, pk=pk)
    if not request.user.is_broker:
        messages.error(request, "ليس لديك صلاحية الوصول لهذه الصفحة")
        return redirect('dashboard')
    
    classes = policy.classes.all()
    return render(request, 'policies/policy_detail.html', {'policy': policy, 'classes': classes})

@login_required
def policy_delete(request, pk):
    policy = get_object_or_404(Policy, pk=pk)
    if not request.user.is_broker:
        messages.error(request, "ليس لديك صلاحية الوصول لهذه الصفحة")
        return redirect('dashboard')
    
    if request.method == 'POST':
        num = policy.policy_number
        policy.delete()
        messages.success(request, f"تم حذف البوليصة رقم {num} بنجاح")
        return redirect('policies:policy_list')
    
    return render(request, 'policies/policy_confirm_delete.html', {'policy': policy})

# --- إدارة الفئات داخل البوليصة ---

@login_required
def policy_class_create(request, policy_pk):
    policy = get_object_or_404(Policy, pk=policy_pk)
    if not request.user.is_broker:
        return redirect('dashboard')

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
def class_benefit_manage(request, class_pk):
    """
    إدارة المنافع لفئة معينة
    """
    policy_class = get_object_or_404(PolicyClass, pk=class_pk)
    if not request.user.is_broker:
        return redirect('dashboard')

    benefits = policy_class.benefits.all().select_related('benefit_type')
    benefit_types = BenefitType.objects.all()

    if request.method == 'POST':
        benefit_id = request.POST.get('benefit_id')
        if benefit_id: # Update
            benefit = get_object_or_404(ClassBenefit, pk=benefit_id)
            form = ClassBenefitForm(request.POST, instance=benefit)
        else: # Create
            form = ClassBenefitForm(request.POST)
        
        if form.is_valid():
            benefit = form.save(commit=False)
            benefit.policy_class = policy_class
            benefit.save()
            messages.success(request, "تم حفظ بيانات المنفعة")
            return redirect('policies:class_benefit_manage', class_pk=policy_class.pk)

    return render(request, 'policies/benefit_manage.html', {
        'policy_class': policy_class,
        'benefits': benefits,
        'benefit_types': benefit_types,
    })

@login_required
def benefit_type_list(request):
    if not request.user.is_broker:
        return redirect('dashboard')
    
    types = BenefitType.objects.all()
    return render(request, 'policies/benefit_type_list.html', {'types': types})
