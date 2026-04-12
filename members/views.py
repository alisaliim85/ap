from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Member
from .forms import MemberForm
from clients.models import Client
from accounts.models import User
from networks.models import ServiceProvider

# ==========================================
# دالة مساعدة: عزل البيانات للمشتركين (Data Isolation)
# ==========================================
def get_allowed_members(user):
    """
    تُرجع المشتركين المسموح للمستخدم رؤيتهم بناءً على دوره.
    """
    # 1. السوبر أدمن يرى كل المشتركين
    if user.role == User.Roles.SUPER_ADMIN:
        return Member.objects.all()
        
    # 2. الوسيط يرى مشتركي العملاء التابعين لشركته فقط
    elif user.is_broker_role and user.related_broker:
        return Member.objects.filter(client__broker=user.related_broker)
        
    # 3. مدير الموارد البشرية (HR) يرى مشتركي شركته فقط
    elif user.is_hr_role and user.related_client:
        return Member.objects.filter(client=user.related_client)
        
    # 4. العضو نفسه (يرى نفسه والتابعين له فقط)
    elif user.is_member_role and hasattr(user, 'member_profile'):
        return Member.objects.filter(
            Q(id=user.member_profile.id) | Q(sponsor=user.member_profile)
        )
        
    return Member.objects.none()

# ==========================================

@login_required
@permission_required('members.view_member', raise_exception=True)
def member_list(request):
    """
    عرض قائمة أعضاء التأمين - [تم تطبيق العزل]
    """
    # استخدام الدالة المساعدة لضمان الأمان بدلاً من Member.objects.all()
    members_list = get_allowed_members(request.user).select_related('client', 'policy_class__policy', 'policy_class__network', 'sponsor').order_by('-created_at')

    # البحث والفلاتر
    search_query = request.GET.get('search', '')
    client_filter = request.GET.get('client', '')
    relation_filter = request.GET.get('relation', '')

    if search_query:
        members_list = members_list.filter(
            Q(full_name__icontains=search_query) |
            Q(medical_card_number__icontains=search_query) |
            Q(national_id__icontains=search_query)
        )
    
    if client_filter:
        members_list = members_list.filter(client_id=client_filter)
    
    if relation_filter:
        members_list = members_list.filter(relation=relation_filter)

    # الترقيم
    paginator = Paginator(members_list, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # للفلترة في القالب (نجلب فقط العملاء المسموحين لهذا المستخدم بدلاً من كل العملاء)
    if request.user.role == User.Roles.SUPER_ADMIN:
        clients = Client.objects.all()
    elif request.user.is_broker_role and request.user.related_broker:
        clients = Client.objects.filter(broker=request.user.related_broker)
    else:
        clients = []

    context = {
        'members': page_obj,
        'page_obj': page_obj,
        'clients': clients,
        'relations': Member.RelationType.choices
    }

    if request.headers.get('HX-Request'):
        return render(request, 'members/partials/member_table.html', context)

    return render(request, 'members/member_list.html', context)

@login_required
@permission_required('members.view_member', raise_exception=True)
def member_detail(request, pk):
    """
    تفاصيل العضو - [محمية تلقائياً بدالة get_allowed_members]
    """
    # إذا حاول وسيط إدخال ID لمشترك لا يتبع له، سيعطيه 404
    member = get_object_or_404(get_allowed_members(request.user).select_related('client', 'policy_class__policy', 'policy_class__network', 'sponsor'), pk=pk)
    
    dependents = member.dependents.select_related('policy_class').all()
    
    return render(request, 'members/member_detail.html', {
        'member': member,
        'dependents': dependents
    })

@login_required
@permission_required('members.add_member', raise_exception=True)
def member_create(request):
    client_id = request.GET.get('client_id')
    sponsor_id = request.GET.get('sponsor_id')
    relation_type = request.GET.get('relation', 'PRINCIPAL')

    if request.method == 'POST':
        # نمرر الـ user ليتمكن الـ Form من فلترة القوائم (العملاء، الكفيل، الفئات)
        form = MemberForm(
            request.POST, 
            user=request.user,
            client_id=client_id,
            relation_type=relation_type,
            sponsor_id=sponsor_id
        )
        if form.is_valid():
            member = form.save()
            messages.success(request, f"تمت إضافة العضو {member.full_name} بنجاح")
            return redirect('members:member_detail', pk=member.pk)
    else:
        form = MemberForm(
            user=request.user, 
            client_id=client_id, 
            relation_type=relation_type,
            sponsor_id=sponsor_id
        )

    return render(request, 'members/member_form.html', {
        'form': form, 
        'title': 'إضافة رقم عضو مأمن جديد'
    })

@login_required
@permission_required('members.change_member', raise_exception=True)
def member_update(request, pk):
    member = get_object_or_404(get_allowed_members(request.user), pk=pk)
    
    if request.method == 'POST':
        form = MemberForm(request.POST, instance=member, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "تم تحديث بيانات العضو بنجاح")
            return redirect('members:member_detail', pk=member.pk)
    else:
        form = MemberForm(instance=member, user=request.user)

    return render(request, 'members/member_form.html', {
        'form': form, 
        'title': f'تعديل بيانات: {member.full_name}',
        'member': member
    })

@login_required
@permission_required('members.delete_member', raise_exception=True)
def member_delete(request, pk):
    member = get_object_or_404(get_allowed_members(request.user), pk=pk)
    
    if request.method == 'POST':
        name = member.full_name
        member.delete()
        messages.success(request, f"تم حذف العضو {name} بنجاح")
        return redirect('members:member_list')
    
    return render(request, 'members/member_confirm_delete.html', {'member': member})


@login_required
def load_policy_classes(request):
    """
    جلب فئات الوثيقة للعميل المحدد عبر AJAX (HTMX)
    تم إضافة حماية العزل لكي لا يطلب وسيط فئات عميل لا يخصه.
    """
    client_id = request.GET.get('client_id')
    if not client_id:
        return render(request, 'members/partials/policy_class_options.html', {'policy_classes': []})
        
    user = request.user
    
    # حماية أمنية (Security Check)
    if user.role == User.Roles.SUPER_ADMIN:
        has_access = True
    elif user.is_broker_role and user.related_broker:
        has_access = Client.objects.filter(id=client_id, broker=user.related_broker).exists()
    elif user.is_hr_role and user.related_client:
        has_access = (str(user.related_client.id) == str(client_id))
    else:
        has_access = False

    if not has_access:
        # إذا لم يكن لديه صلاحية، نرجع قائمة فارغة كنوع من الحماية
        return render(request, 'members/partials/policy_class_options.html', {'policy_classes': []})

    from django.db.models import Q
    from policies.models import PolicyClass
    client_obj = get_object_or_404(Client, id=client_id)
    
    query = Q(policy__client_id=client_id)
    if client_obj.parent_id:
        query |= Q(policy__client_id=client_obj.parent_id, policy__master_policy__isnull=True)
    
    policy_classes = PolicyClass.objects.filter(query).select_related('policy').distinct()
    return render(request, 'members/partials/policy_class_options.html', {'policy_classes': policy_classes})


@login_required
@permission_required('accounts.view_member_dashboard', raise_exception=True)
def my_dashboard(request):
    """لوحة معلومات العضو (لا تحتاج تعديل جوهري لأنها مرتبطة حصراً بملف العضو المسجل)"""
    try:
        current_member = request.user.member_profile
    except Member.DoesNotExist:
        messages.error(request, "لا توجد بيانات عضو مسجلة لهذا المستخدم")
        return render(request, 'members/my_dashboard.html', {'member': None})

    family_count = Member.objects.filter(sponsor=current_member).count()
    
    context = {
        'member': current_member,
        'family_count': family_count,
    }
    return render(request, 'members/my_dashboard.html', context)


@login_required
@permission_required('members.view_my_family_members', raise_exception=True)
def my_family_members(request):
    """أفراد عائلة العضو (مقفلة تلقائياً على العضو الحالي)"""
    try:
        current_member = request.user.member_profile
    except Member.DoesNotExist:
        messages.error(request, "لا توجد بيانات عضو مسجلة لهذا المستخدم")
        return render(request, 'members/my_family_members.html', {'members': []})
    
    members = Member.objects.filter(
        Q(id=current_member.id) | Q(sponsor=current_member)
    ).select_related(
        'client',        
        'policy_class__policy',
        'policy_class__network',
        'sponsor'        
    ).order_by('relation') 
    
    return render(request, 'members/my_family_members.html', {'members': members})

@login_required
def my_hospitals(request):
    """قائمة المستشفيات الخاصة بشبكة العضو (موبيل-فيرست)"""
    try:
        current_member = request.user.member_profile
    except Member.DoesNotExist:
        messages.error(request, "لا توجد بيانات عضو مسجلة لهذا المستخدم")
        return redirect('members:member_dashboard')

    policy_class = current_member.policy_class
    network = policy_class.network if policy_class else None

    if not network:
        hospitals = ServiceProvider.objects.none()
    else:
        hospitals = network.hospitals.all()

    # Filters prep
    cities = hospitals.values_list('city', flat=True).distinct().order_by('city')
    types_choices = ServiceProvider.ProviderTypes.choices

    search_query = request.GET.get('search', '')
    city_filter = request.GET.get('city', '')
    type_filter = request.GET.get('type', '')

    if search_query:
        hospitals = hospitals.filter(
            Q(name_ar__icontains=search_query) | 
            Q(name_en__icontains=search_query) |
            Q(city__icontains=search_query)
        )
    if city_filter:
        hospitals = hospitals.filter(city=city_filter)
    if type_filter:
        hospitals = hospitals.filter(type=type_filter)

    # Ordering for consistent pagination
    hospitals = hospitals.order_by('name_ar')

    paginator = Paginator(hospitals, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'cities': cities,
        'types_choices': types_choices,
        'network': network
    }

    if request.headers.get('HX-Request'):
        return render(request, 'members/partials/hospital_list_content.html', context)

    return render(request, 'members/my_hospitals.html', context)