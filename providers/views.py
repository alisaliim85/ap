from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from .models import Provider
from .forms import ProviderForm

from django.core.paginator import Paginator

@login_required
@permission_required('providers.view_provider', raise_exception=True)
def provider_list(request):
    """
    عرض قائمة شركات التأمين مع دعم الترقيم (Pagination)
    """
    providers_list = Provider.objects.all().order_by('-created_at')

    # منطق البحث (HTMX)
    search_query = request.GET.get('search', '')
    if search_query:
        providers_list = providers_list.filter(name_en__icontains=search_query) | providers_list.filter(name_ar__icontains=search_query) | providers_list.filter(license_number__icontains=search_query)

    # الترقيم (Pagination)
    paginator = Paginator(providers_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # إذا كان الطلب من HTMX، نعيد فقط الجدول (Partial)
    if request.headers.get('HX-Request'):
        return render(request, 'providers/partials/provider_table.html', {'providers': page_obj, 'page_obj': page_obj})

    return render(request, 'providers/provider_list.html', {'providers': page_obj, 'page_obj': page_obj})

@login_required
@permission_required('providers.add_provider', raise_exception=True)
def provider_create(request):
    if request.method == 'POST':
        form = ProviderForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "تمت إضافة شركة التأمين بنجاح")
            return redirect('provider_list')
    else:
        form = ProviderForm()

    return render(request, 'providers/provider_form.html', {'form': form, 'title': 'إضافة شركة تأمين جديدة'})

@login_required
@permission_required('providers.change_provider', raise_exception=True)
def provider_update(request, pk):
    provider = get_object_or_404(Provider, pk=pk)

    if request.method == 'POST':
        form = ProviderForm(request.POST, request.FILES, instance=provider)
        if form.is_valid():
            form.save()
            messages.success(request, "تم تحديث بيانات شركة التأمين بنجاح")
            return redirect('provider_list')
    else:
        form = ProviderForm(instance=provider)

    return render(request, 'providers/provider_form.html', {'form': form, 'title': f'تعديل شركة: {provider.name_ar}', 'provider': provider})

@login_required
@permission_required('providers.delete_provider', raise_exception=True)
def provider_delete(request, pk):
    provider = get_object_or_404(Provider, pk=pk)
    
    if request.method == 'POST':
        name = provider.name_ar
        provider.delete()
        messages.success(request, f"تم حذف شركة التأمين {name} بنجاح")
        return redirect('provider_list')
    
    return render(request, 'providers/provider_confirm_delete.html', {'provider': provider})

@login_required
@permission_required('providers.view_provider', raise_exception=True)
def provider_detail(request, pk):
    provider = get_object_or_404(Provider, pk=pk)
    
    return render(request, 'providers/provider_detail.html', {'provider': provider})
