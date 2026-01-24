from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import ServiceProvider, Network
from .forms import ServiceProviderForm, NetworkForm

# --- إدارة مقدمي الخدمة (Hospitals/Clinics) ---

@login_required
def service_provider_list(request):
    """
    قائمة بجميع مقدمي الخدمة الطبية
    """
    if not request.user.is_broker:
        return redirect('dashboard')

    providers = ServiceProvider.objects.all().order_by('name_ar')

    # البحث
    search_query = request.GET.get('search', '')
    if search_query:
        providers = providers.filter(
            Q(name_ar__icontains=search_query) |
            Q(name_en__icontains=search_query) |
            Q(city__icontains=search_query)
        )

    # الترقيم
    paginator = Paginator(providers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.headers.get('HX-Request'):
        return render(request, 'networks/partials/provider_table.html', {'providers': page_obj, 'page_obj': page_obj})

    return render(request, 'networks/provider_list.html', {'providers': page_obj, 'page_obj': page_obj})

@login_required
def service_provider_create(request):
    if not request.user.is_broker:
        return redirect('dashboard')

    if request.method == 'POST':
        form = ServiceProviderForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "تمت إضافة مقدم الخدمة بنجاح")
            return redirect('networks:service_provider_list')
    else:
        form = ServiceProviderForm()

    return render(request, 'networks/provider_form.html', {'form': form, 'title': 'إضافة مقدم خدمة جديد'})

@login_required
def service_provider_update(request, pk):
    provider = get_object_or_404(ServiceProvider, pk=pk)
    if not request.user.is_broker:
        return redirect('dashboard')

    if request.method == 'POST':
        form = ServiceProviderForm(request.POST, instance=provider)
        if form.is_valid():
            form.save()
            messages.success(request, "تم تحديث بيانات مقدم الخدمة")
            return redirect('networks:service_provider_list')
    else:
        form = ServiceProviderForm(instance=provider)

    return render(request, 'networks/provider_form.html', {'form': form, 'title': f'تعديل مقدم الخدمة: {provider.name_ar}'})

@login_required
def service_provider_delete(request, pk):
    provider = get_object_or_404(ServiceProvider, pk=pk)
    if request.method == 'POST':
        name = provider.name_ar
        provider.delete()
        messages.success(request, f"تم حذف {name} بنجاح")
        return redirect('networks:service_provider_list')
    return render(request, 'networks/provider_confirm_delete.html', {'provider': provider})

# --- إدارة الشبكات الطبية (Networks) ---

@login_required
def network_list(request):
    if not request.user.is_broker:
        return redirect('dashboard')

    networks = Network.objects.all().select_related('provider').order_by('provider__name_ar', 'name_ar')
    return render(request, 'networks/network_list.html', {'networks': networks})

@login_required
def network_create(request):
    if not request.user.is_broker:
        return redirect('dashboard')

    if request.method == 'POST':
        form = NetworkForm(request.POST)
        if form.is_valid():
            network = form.save()
            messages.success(request, "تمت إضافة الشبكة بنجاح")
            return redirect('networks:network_list')
    else:
        form = NetworkForm()

    return render(request, 'networks/network_form.html', {'form': form, 'title': 'إضافة شبكة جديدة'})

@login_required
def network_update(request, pk):
    network = get_object_or_404(Network, pk=pk)
    if not request.user.is_broker:
        return redirect('dashboard')

    if request.method == 'POST':
        form = NetworkForm(request.POST, instance=network)
        if form.is_valid():
            form.save()
            messages.success(request, "تم تحديث بيانات الشبكة")
            return redirect('networks:network_list')
    else:
        form = NetworkForm(instance=network)

    return render(request, 'networks/network_form.html', {'form': form, 'title': f'تعديل الشبكة: {network.name_ar}'})

@login_required
def network_manage_hospitals(request, pk):
    """
    إدارة المستشفيات داخل الشبكة (إضافة/حذف)
    """
    network = get_object_or_404(Network, pk=pk)
    if not request.user.is_broker:
        return redirect('dashboard')

    # التعامل مع طلبات التبديل (HTMX)
    if request.method == 'POST' and request.headers.get('HX-Request'):
        hospital_id = request.POST.get('hospital_id')
        action = request.POST.get('action')
        hospital = get_object_or_404(ServiceProvider, pk=hospital_id)
        
        if action == 'add':
            network.hospitals.add(hospital)
        elif action == 'remove':
            network.hospitals.remove(hospital)
            
        return render(request, 'networks/partials/hospital_status_btn.html', {
            'hospital': hospital, 
            'network': network,
            'is_in_network': hospital in network.hospitals.all()
        })

    # العرض العادي
    all_hospitals = ServiceProvider.objects.all().order_by('name_ar')
    
    # البحث داخل القائمة
    search_query = request.GET.get('search', '')
    if search_query:
        all_hospitals = all_hospitals.filter(
            Q(name_ar__icontains=search_query) |
            Q(city__icontains=search_query)
        )

    # الترقيم
    paginator = Paginator(all_hospitals, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'network': network,
        'page_obj': page_obj,
        'hospitals_in_network': network.hospitals.all()
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'networks/partials/hospital_selection_list.html', context)

    return render(request, 'networks/manage_hospitals.html', context)
