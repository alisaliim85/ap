from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Member
from .forms import MemberForm
from clients.models import Client

@login_required
@permission_required('members.view_member', raise_exception=True)
def member_list(request):
    """
    عرض قائمة أعضاء التأمين
    """
    members_list = Member.objects.all().select_related('client', 'policy_class__policy', 'policy_class__network', 'sponsor').order_by('-created_at')

    # تصفية الصلاحيات (HR)
    if request.user.has_perm('accounts.view_hr_dashboard') and not request.user.has_perm('accounts.view_broker_dashboard'):
         members_list = members_list.filter(client=request.user.related_client)

    # البحث والفلاتر
    search_query = request.GET.get('search', '')
    client_filter = request.GET.get('client', '')
    relation_filter = request.GET.get('relation', '')

    if search_query:
        members_list = members_list.filter(
            Q(full_name__icontains=search_query) |
            Q(medical_card_number__icontains=search_query)
        )
    
    if client_filter:
        members_list = members_list.filter(client_id=client_filter)
    
    if relation_filter:
        members_list = members_list.filter(relation=relation_filter)

    # الترقيم
    paginator = Paginator(members_list, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # للفلترة في القالب
    clients = Client.objects.all() if request.user.has_perm('accounts.view_broker_dashboard') else []

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
    member = get_object_or_404(Member.objects.select_related('client', 'policy_class__policy', 'policy_class__network', 'sponsor'), pk=pk)
    
    # التحقق من الصلاحية
    if request.user.has_perm('accounts.view_hr_dashboard') and not request.user.has_perm('accounts.view_broker_dashboard'):
        if member.client != request.user.related_client:
            messages.error(request, "لا يمكنك الوصول لبيانات هذا العضو")
            return redirect('members:member_list')

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
    member = get_object_or_404(Member, pk=pk)
    
    if request.user.has_perm('accounts.view_hr_dashboard') and not request.user.has_perm('accounts.view_broker_dashboard'):
         if member.client != request.user.related_client:
            return redirect('members:member_list')

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
    member = get_object_or_404(Member, pk=pk)
    if request.user.has_perm('accounts.view_hr_dashboard') and not request.user.has_perm('accounts.view_broker_dashboard'):
         if member.client != request.user.related_client:
            return redirect('members:member_list')

    if request.method == 'POST':
        name = member.full_name
        member.delete()
        messages.success(request, f"تم حذف العضو {name} بنجاح")
        return redirect('members:member_list')
    
    return render(request, 'members/member_confirm_delete.html', {'member': member})
@login_required
def load_policy_classes(request):
    client_id = request.GET.get('client_id')
    if not client_id:
        return render(request, 'members/partials/policy_class_options.html', {'policy_classes': []})
        
    from django.db.models import Q
    from policies.models import PolicyClass
    client_obj = get_object_or_404(Client, id=client_id)
    
    query = Q(policy__client_id=client_id)
    if client_obj.parent_id:
        query |= Q(policy__client_id=client_obj.parent_id, policy__master_policy__isnull=True)
    
    policy_classes = PolicyClass.objects.filter(query).select_related('policy').distinct()
    return render(request, 'members/partials/policy_class_options.html', {'policy_classes': policy_classes})
