from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from .models import Partner
from .forms import PartnerForm
from accounts.models import User

# ==========================================
# دالة مساعدة: عزل البيانات للشركاء (Data Isolation)
# ==========================================
def get_allowed_partners(user):
    """
    تُرجع الشركاء المسموح للمستخدم رؤيتهم بناءً على دوره.
    """
    # 1. السوبر أدمن يرى كل الشركاء المسجلين في المنصة
    if user.role == User.Roles.SUPER_ADMIN:
        return Partner.objects.all()
        
    # 2. الوسيط يرى فقط الشركاء الذين يمتلك عقداً نشطاً معهم
    elif user.is_broker_role and user.related_broker:
        return Partner.objects.filter(
            broker_contracts__broker=user.related_broker,
            broker_contracts__is_active=True
        ).distinct()
        
    # 3. موظفو الشريك (صيدلي، الخ) يرون ملف شركتهم فقط
    elif user.is_partner_role and user.related_partner:
        return Partner.objects.filter(id=user.related_partner.id)
        
    return Partner.objects.none()

# ==========================================

@login_required
@permission_required('partners.view_partner', raise_exception=True)
def partner_list(request):
    """
    عرض قائمة الشركاء والمزودين مع دعم الترقيم (Pagination) - [تم تطبيق العزل]
    """
    # جلب الشركاء المسموح بهم فقط
    partners_list = get_allowed_partners(request.user).order_by('-created_at')

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
@permission_required('partners.add_partner', raise_exception=True)
def partner_create(request):
    """
    إضافة شريك جديد (غالباً هذه الصلاحية تكون للسوبر أدمن فقط في نظام الـ Marketplace)
    """
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
@permission_required('partners.change_partner', raise_exception=True)
def partner_update(request, pk):
    """
    تعديل بيانات الشريك - [محمية]
    """
    partner = get_object_or_404(get_allowed_partners(request.user), pk=pk)

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
@permission_required('partners.delete_partner', raise_exception=True)
def partner_delete(request, pk):
    """
    حذف شريك - [محمية]
    """
    partner = get_object_or_404(get_allowed_partners(request.user), pk=pk)
    
    if request.method == 'POST':
        name = partner.name_ar
        partner.delete()
        messages.success(request, f"تم حذف الشريك {name} بنجاح")
        return redirect('partner_list')
    
    return render(request, 'partners/partner_confirm_delete.html', {'partner': partner})

@login_required
@permission_required('partners.view_partner', raise_exception=True)
def partner_detail(request, pk):
    """
    تفاصيل الشريك - [محمية]
    """
    partner = get_object_or_404(get_allowed_partners(request.user), pk=pk)
    
    return render(request, 'partners/partner_detail.html', {'partner': partner})