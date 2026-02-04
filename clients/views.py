from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Count, Sum, Q
from .models import Client
from .forms import ClientForm
from policies.models import Policy
from members.models import Member

from django.core.paginator import Paginator

@login_required
@permission_required('clients.view_client_dashboard', raise_exception=True)
def client_list(request):
    """
    عرض قائمة العملاء مع دعم البحث والترقيم (Pagination)
    """
    clients_list = Client.objects.select_related('parent').all().order_by('-created_at')

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
@permission_required('clients.manage_clients', raise_exception=True)
def client_create(request):
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
@permission_required('clients.manage_clients', raise_exception=True)
def client_update(request, pk):
    client = get_object_or_404(Client, pk=pk)

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
@permission_required('clients.manage_clients', raise_exception=True)
def client_delete(request, pk):
    client = get_object_or_404(Client, pk=pk)
    
    if request.method == 'POST':
        name = client.name_ar
        client.delete()
        messages.success(request, f"تم حذف الشركة {name} بنجاح")
        return redirect('client_list')
    
    return render(request, 'clients/client_confirm_delete.html', {'client': client})

@login_required
@permission_required('clients.view_client_dashboard', raise_exception=True)
def client_detail(request, pk):
    client = get_object_or_404(Client, pk=pk)
    
    # --- أولاً: حالة الشركة القابضة (Holding Company) ---
    if client.is_holding:
        # 1. إحصائيات الشركات التابعة
        subsidiaries = client.subsidiaries.all().annotate(
            total_employees=Count('members', filter=Q(members__relation='PRINCIPAL')),
            total_spouses=Count('members', filter=Q(members__relation='SPOUSE')),
            total_children=Count('members', filter=Q(members__relation='CHILD')),
            total_lives=Count('members')
        )
        
        # 2. الوثيقة الرئيسية (Master Policy)
        master_policy = Policy.objects.filter(client=client, master_policy__isnull=True).select_related('provider').prefetch_related(
            'classes',
            'classes__network',
            'classes__benefits',
            'classes__benefits__benefit_type'
        ).first()
        
        # 3. بيانات التعداد (الأعضاء التابعين للقابضة أو الشركات التابعة لها)
        all_members = Member.objects.filter(
            Q(client=client) | Q(client__parent=client)
        )
        
        census = {
            'employees': all_members.filter(relation='PRINCIPAL').count(),
            'spouses': all_members.filter(relation='SPOUSE').count(),
            'children': all_members.filter(relation='CHILD').count(),
            'total': all_members.count()
        }
        
        # 4. توزيع الفئات
        class_stats = all_members.values('policy_class__name').annotate(
            count=Count('id')
        ).order_by('-count')

        # 5. الشبكة الطبية (من الوثيقة الرئيسية)
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

    # --- ثانياً: حالة الشركة التابعة (Subsidiary) أو المستقلة ---
    else:
        # 1. جلب الوثيقة الخاصة بهذه الشركة
        policy = Policy.objects.filter(client=client).select_related('master_policy').first()
        network = None
        
        if policy:
            # محاولة جلب الشبكة من فئات الوثيقة الحالية
            first_class = policy.classes.first()
            if first_class and first_class.network:
                network = first_class.network
            
            # إذا لم توجد شبكة، وكانت الوثيقة مرتبطة بوثيقة أم (Holding Master Policy)
            elif policy.master_policy:
                master_class = policy.master_policy.classes.first()
                if master_class:
                    network = master_class.network

        # 2. إحصائيات الشركة الحالية فقط
        members = Member.objects.filter(client=client)
        census = {
            'employees': members.filter(relation='PRINCIPAL').count(),
            'dependents': members.exclude(relation='PRINCIPAL').count(),
            'total': members.count()
        }

        context = {
            'client': client,
            'policy': policy,
            'network': network,
            'census': census,
        }
        return render(request, 'clients/client_detail.html', context)