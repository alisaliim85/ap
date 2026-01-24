from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Partner
from .forms import PartnerForm

from django.core.paginator import Paginator

@login_required
def partner_list(request):
    """
    عرض قائمة الشركاء والمزودين مع دعم الترقيم (Pagination)
    """
    if not request.user.is_broker:
        messages.error(request, "ليس لديك صلاحية الوصول لهذه الصفحة")
        return redirect('dashboard')

    partners_list = Partner.objects.all().order_by('-created_at')

    # منطق البحث (HTMX)
    search_query = request.GET.get('search', '')
    if search_query:
        partners_list = partners_list.filter(name_en__icontains=search_query) | \
                   partners_list.filter(name_ar__icontains=search_query) | \
                   partners_list.filter(commercial_record__icontains=search_query)

    # الترقيم (Pagination)
    paginator = Paginator(partners_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # إذا كان الطلب من HTMX، نعيد فقط الجدول (Partial)
    if request.headers.get('HX-Request'):
        return render(request, 'partners/partials/partner_table.html', {'partners': page_obj, 'page_obj': page_obj})

    return render(request, 'partners/partner_list.html', {'partners': page_obj, 'page_obj': page_obj})

@login_required
def partner_create(request):
    if not request.user.is_broker:
        messages.error(request, "ليس لديك صلاحية الوصول لهذه الصفحة")
        return redirect('dashboard')

    if request.method == 'POST':
        form = PartnerForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "تمت إضافة الشريك بنجاح")
            return redirect('partner_list')
    else:
        form = PartnerForm()

    return render(request, 'partners/partner_form.html', {'form': form, 'title': 'إضافة شريك جديد'})

@login_required
def partner_update(request, pk):
    partner = get_object_or_404(Partner, pk=pk)
    if not request.user.is_broker:
        messages.error(request, "ليس لديك صلاحية الوصول لهذه الصفحة")
        return redirect('dashboard')

    if request.method == 'POST':
        form = PartnerForm(request.POST, request.FILES, instance=partner)
        if form.is_valid():
            form.save()
            messages.success(request, "تم تحديث بيانات الشريك بنجاح")
            return redirect('partner_list')
    else:
        form = PartnerForm(instance=partner)

    return render(request, 'partners/partner_form.html', {'form': form, 'title': f'تعديل شريك: {partner.name_ar}', 'partner': partner})

@login_required
def partner_delete(request, pk):
    partner = get_object_or_404(Partner, pk=pk)
    if not request.user.is_broker:
        messages.error(request, "ليس لديك صلاحية الوصول لهذه الصفحة")
        return redirect('dashboard')
    
    if request.method == 'POST':
        name = partner.name_ar
        partner.delete()
        messages.success(request, f"تم حذف الشريك {name} بنجاح")
        return redirect('partner_list')
    
    return render(request, 'partners/partner_confirm_delete.html', {'partner': partner})

@login_required
def partner_detail(request, pk):
    partner = get_object_or_404(Partner, pk=pk)
    if not request.user.is_broker:
        messages.error(request, "ليس لديك صلاحية الوصول لهذه الصفحة")
        return redirect('dashboard')
    
    return render(request, 'partners/partner_detail.html', {'partner': partner})
