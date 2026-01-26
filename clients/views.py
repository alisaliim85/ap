from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum, Q
from .models import Client
from .forms import ClientForm
from policies.models import Policy
from members.models import Member

from django.core.paginator import Paginator

@login_required
def client_list(request):
    """
    عرض قائمة العملاء مع دعم البحث والترقيم (Pagination)
    """
    if not request.user.is_broker:
        messages.error(request, "ليس لديك صلاحية الوصول لهذه الصفحة")
        return redirect('dashboard')

    clients_list = Client.objects.all().order_by('-created_at')

    # منطق البحث (HTMX)
    search_query = request.GET.get('search', '')
    if search_query:
        clients_list = clients_list.filter(name_en__icontains=search_query) | clients_list.filter(name_ar__icontains=search_query)

    # الترقيم (Pagination)
    paginator = Paginator(clients_list, 10) # 10 عملاء في الصفحة
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # إذا كان الطلب من HTMX، نعيد فقط الجدول (Partial)
    if request.headers.get('HX-Request'):
        return render(request, 'clients/partials/client_table.html', {'clients': page_obj, 'page_obj': page_obj})

    return render(request, 'clients/client_list.html', {'clients': page_obj, 'page_obj': page_obj})

@login_required
def client_create(request):
    if not request.user.is_broker:
        messages.error(request, "ليس لديك صلاحية الوصول لهذه الصفحة")
        return redirect('dashboard')

    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "تمت إضافة الشركة بنجاح")
            return redirect('client_list')
    else:
        form = ClientForm()

    return render(request, 'clients/client_form.html', {'form': form, 'title': 'إضافة شركة جديدة'})

@login_required
def client_update(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if not request.user.is_broker:
        messages.error(request, "ليس لديك صلاحية الوصول لهذه الصفحة")
        return redirect('dashboard')

    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, "تم تحديث بيانات الشركة بنجاح")
            return redirect('client_list')
    else:
        form = ClientForm(instance=client)

    return render(request, 'clients/client_form.html', {'form': form, 'title': f'تعديل شركة: {client.name_ar}', 'client': client})

@login_required
def client_delete(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if not request.user.is_broker:
        messages.error(request, "ليس لديك صلاحية الوصول لهذه الصفحة")
        return redirect('dashboard')
    
    if request.method == 'POST':
        name = client.name_ar
        client.delete()
        messages.success(request, f"تم حذف الشركة {name} بنجاح")
        return redirect('client_list')
    
    return render(request, 'clients/client_confirm_delete.html', {'client': client})

@login_required
def client_detail(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if not request.user.is_broker:
        messages.error(request, "ليس لديك صلاحية الوصول لهذه الصفحة")
        return redirect('dashboard')
    
    # Check if this is a specialized dashboard for Holding Company
    if client.is_holding:
        # 1. Basic Stats
        subsidiaries = client.subsidiaries.all().annotate(
            total_employees=Count('members', filter=Q(members__relation='PRINCIPAL')),
            total_spouses=Count('members', filter=Q(members__relation='SPOUSE')),
            total_children=Count('members', filter=Q(members__relation='CHILD')),
            total_lives=Count('members')
        )
        
        # 2. Master Policy & Benefits
        master_policy = Policy.objects.filter(client=client, master_policy__isnull=True).first()
        
        # 3. Census Data (Aggregated from all subsidiaries + holding)
        # We need members linked to holding OR its subsidiaries
        all_members = Member.objects.filter(
            Q(client=client) | Q(client__parent=client)
        )
        
        census = {
            'employees': all_members.filter(relation='PRINCIPAL').count(),
            'spouses': all_members.filter(relation='SPOUSE').count(),
            'children': all_members.filter(relation='CHILD').count(),
            'total': all_members.count()
        }
        
        # 4. Class Distribution Stats
        # Group by policy class name and count members
        class_stats = all_members.values('policy_class__name').annotate(
            count=Count('id')
        ).order_by('-count')

        # 5. Network (from master policy classes)
        network = None
        if master_policy and master_policy.classes.exists():
            network = master_policy.classes.first().network

        context = {
            'client': client,
            'subsidiaries': subsidiaries,
            'master_policy': master_policy,
            'census': census,
            'class_stats': class_stats,
            'network': network
        }
        return render(request, 'clients/client_detail_holding.html', context)

    return render(request, 'clients/client_detail.html', {'client': client})