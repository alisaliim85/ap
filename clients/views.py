from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Client
from .forms import ClientForm

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
    
    return render(request, 'clients/client_detail.html', {'client': client})