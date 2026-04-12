from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db import transaction
from django.db.models import Q

from .models import RequestType, ServiceRequest, RequestAttachment
from .forms import ServiceRequestCreateForm, validate_dynamic_data
from members.models import Member
from accounts.models import User


# ==========================================
# دالة مساعدة: الحماية الجوهرية (Data Isolation)
# ==========================================
def get_allowed_requests(user):
    """
    حارس البوابة لجميع الطلبات — يضمن عزل البيانات حسب الدور.
    """
    base_qs = ServiceRequest.objects.select_related(
        'request_type', 'member', 'member__client', 'submitted_by'
    )

    # 1. السوبر أدمن يرى كل شيء
    if user.role == User.Roles.SUPER_ADMIN:
        return base_qs

    # 2. الوسيط يرى طلبات الشركات التابعة له
    elif user.is_broker_role and user.related_broker:
        return base_qs.filter(member__client__broker=user.related_broker)

    # 3. الـ HR يرى طلبات شركته فقط
    elif user.is_hr_role and user.related_client:
        return base_qs.filter(member__client=user.related_client)

    # 4. العضو يرى طلباته وطلبات التابعين له
    elif user.is_member_role and hasattr(user, 'member_profile'):
        return base_qs.filter(
            Q(member=user.member_profile) | Q(member__sponsor=user.member_profile)
        )

    return ServiceRequest.objects.none()


# ==========================================
# عرض قائمة الطلبات
# ==========================================
@login_required
def request_list(request):
    user = request.user
    requests_qs = get_allowed_requests(user)

    # الوسيط لا يرى المسودات
    if user.is_broker_role:
        requests_qs = requests_qs.exclude(status=ServiceRequest.Status.DRAFT)

    # فلترة بالحالة
    status_filter = request.GET.get('status', '')
    if status_filter:
        requests_qs = requests_qs.filter(status=status_filter)

    # فلترة بالنوع
    type_filter = request.GET.get('type', '')
    if type_filter:
        requests_qs = requests_qs.filter(request_type_id=type_filter)

    # بحث
    search = request.GET.get('search', '').strip()
    if search:
        requests_qs = requests_qs.filter(
            Q(reference__icontains=search)
            | Q(member__full_name__icontains=search)
            | Q(member__national_id__icontains=search)
        )

    requests_qs = requests_qs.order_by('-created_at')
    request_types = RequestType.objects.filter(is_active=True)

    context = {
        'service_requests': requests_qs,
        'request_types': request_types,
        'status_choices': ServiceRequest.Status.choices,
        'current_status': status_filter,
        'current_type': type_filter,
        'search_query': search,
    }

    # دعم HTMX partial
    if request.htmx:
        return render(request, 'service_requests/partials/request_table.html', context)

    return render(request, 'service_requests/request_list.html', context)


# ==========================================
# عرض تفاصيل الطلب
# ==========================================
@login_required
def request_detail(request, pk):
    sreq = get_object_or_404(
        get_allowed_requests(request.user).prefetch_related(
            'attachments',
            'status_logs__user',
        ),
        pk=pk
    )
    # تجهيز الحقول الديناميكية مع قيمها للعرض في القالب
    fields_schema = sreq.request_type.fields_schema or []
    data = sreq.data or {}
    fields_with_values = []
    for field in fields_schema:
        fields_with_values.append({
            'label': field.get('label', field.get('name', '')),
            'type': field.get('type', 'text'),
            'value': data.get(field.get('name', ''), ''),
        })

    context = {
        'sreq': sreq,
        'fields_with_values': fields_with_values,
    }
    return render(request, 'service_requests/request_detail.html', context)


@login_required
def request_edit(request, pk):
    sreq = get_object_or_404(get_allowed_requests(request.user), pk=pk)
    
    # Only allow editing if DRAFT or RETURNED
    if sreq.status not in [ServiceRequest.Status.DRAFT, ServiceRequest.Status.RETURNED]:
        messages.error(request, "لا يمكن تعديل الطلب في حالته الحالية.")
        return redirect('service_requests:request_detail', pk=pk)

    user = request.user
    request_types = RequestType.objects.filter(is_active=True).order_by('display_order')

    if request.method == 'POST':
        form = ServiceRequestCreateForm(request.POST, request.FILES, user=user)
        # Handle dynamic fields validation
        cleaned_data_dynamic, dynamic_errors = validate_dynamic_data(
            sreq.request_type.fields_schema or [], request.POST
        )

        if form.is_valid() and not dynamic_errors:
            try:
                with transaction.atomic():
                    sreq.member = form.cleaned_data['member']
                    sreq.data = cleaned_data_dynamic
                    # If this is a RETURNED request, moving it back to submittable state
                    sreq.save()

                    # Handle new attachments
                    attachments = request.FILES.getlist('attachments')
                    for f in attachments:
                        RequestAttachment.objects.create(service_request=sreq, file=f)

                    action = request.POST.get('action', 'draft')
                    if action == 'submit':
                        sreq.submit(user=user)
                        messages.success(request, "تم تحديث الطلب وإرساله بنجاح.")
                    else:
                        messages.success(request, "تم تحديث المسودة بنجاح.")

                return redirect('service_requests:request_detail', pk=sreq.pk)
            except Exception as e:
                messages.error(request, f"خطأ: {str(e)}")
    else:
        # Pre-populate form
        initial_data = {
            'request_type': sreq.request_type.id,
            'member': sreq.member.id,
            'national_id_search': sreq.member.national_id,
        }
        form = ServiceRequestCreateForm(initial=initial_data, user=user)

    context = {
        'form': form,
        'sreq': sreq,
        'request_types': request_types,
        'is_edit': True,
        'dynamic_data': sreq.data,
    }
    return render(request, 'service_requests/request_create.html', context)


@login_required
def request_delete(request, pk):
    sreq = get_object_or_404(get_allowed_requests(request.user), pk=pk)
    
    # Security check: Usually only allow deleting drafts, or based on specific perms
    if sreq.status != ServiceRequest.Status.DRAFT and not request.user.is_superuser:
        messages.error(request, "لا يمكن حذف الطلبات غير المسودة.")
        return redirect('service_requests:request_list')

    if request.method == 'POST':
        sreq.delete()
        messages.success(request, "تم حذف الطلب بنجاح.")
        return redirect('service_requests:request_list')

    return render(request, 'service_requests/request_confirm_delete.html', {'sreq': sreq})


@login_required
@require_POST
def add_attachment(request, pk):
    sreq = get_object_or_404(get_allowed_requests(request.user), pk=pk)
    files = request.FILES.getlist('attachments')
    
    if files:
        for f in files:
            RequestAttachment.objects.create(service_request=sreq, file=f)
        messages.success(request, f"تم إضافة {len(files)} مرفق(ات) بنجاح.")
    else:
        messages.error(request, "يرجى اختيار ملفات للإرفاق.")
        
    return redirect('service_requests:request_detail', pk=pk)


# ==========================================
# إنشاء طلب جديد
# ==========================================
@login_required
def request_create(request):
    user = request.user
    request_types = RequestType.objects.filter(is_active=True).order_by('display_order')

    if request.method == 'POST':
        form = ServiceRequestCreateForm(request.POST, request.FILES, user=user)
        type_id = request.POST.get('request_type')

        # جلب نوع الطلب
        try:
            req_type = RequestType.objects.get(id=type_id, is_active=True)
        except (RequestType.DoesNotExist, ValueError, TypeError):
            messages.error(request, "نوع الطلب غير صالح.")
            return render(request, 'service_requests/request_create.html', {
                'form': form, 'request_types': request_types,
            })

        # التحقق من الحقول الديناميكية
        cleaned_data_dynamic, dynamic_errors = validate_dynamic_data(
            req_type.fields_schema or [], request.POST
        )

        if form.is_valid() and not dynamic_errors:
            action = request.POST.get('action', 'draft')
            member = form.cleaned_data['member']

            try:
                with transaction.atomic():
                    sreq = ServiceRequest(
                        request_type=req_type,
                        member=member,
                        submitted_by=user,
                        submitted_on_behalf=not user.is_member_role,
                        data=cleaned_data_dynamic,
                    )
                    sreq.save()

                    # حفظ المرفقات
                    attachments = request.FILES.getlist('attachments')
                    for f in attachments:
                        RequestAttachment.objects.create(service_request=sreq, file=f)

                    if action == 'submit':
                        sreq.submit(user=user)
                        messages.success(request, "تم حفظ الطلب وإرساله بنجاح.")
                    else:
                        messages.success(request, "تم حفظ الطلب كمسودة.")

                return redirect('service_requests:request_detail', pk=sreq.pk)

            except ValueError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"حدث خطأ غير متوقع: {str(e)}")
        else:
            # إذا كانت هناك أخطاء في الحقول الديناميكية
            if dynamic_errors:
                for field_name, error_msg in dynamic_errors.items():
                    messages.error(request, error_msg)
    else:
        form = ServiceRequestCreateForm(user=user)

    context = {
        'form': form,
        'request_types': request_types,
    }
    return render(request, 'service_requests/request_create.html', context)


# ==========================================
# HTMX: جلب الحقول الديناميكية حسب نوع الطلب
# ==========================================
@login_required
def request_type_fields(request, type_id):
    """
    HTMX partial — يُرجع حقول الإدخال الديناميكية حسب نوع الطلب المختار.
    """
    try:
        req_type = RequestType.objects.get(id=type_id, is_active=True)
    except RequestType.DoesNotExist:
        return render(request, 'service_requests/partials/dynamic_fields.html', {
            'fields': [], 'request_type': None
        })

    # Get current values if provided (for editing)
    values = {}
    for key in request.GET:
        if key.startswith('dynamic_'):
            values[key.replace('dynamic_', '')] = request.GET[key]

    return render(request, 'service_requests/partials/dynamic_fields.html', {
        'fields': req_type.fields_schema or [],
        'request_type': req_type,
        'values': values,
    })


# ==========================================
# بحث عن عضو برقم الهوية (HR / Broker)
# ==========================================
@login_required
def search_member_by_nid(request):
    # نستخدم الاسم المرسل من الفورم (national_id_search)
    q = request.GET.get('national_id_search', '').strip()
    user = request.user

    if len(q) < 5:
        return render(request, 'service_requests/partials/member_search_result.html', {'member': None})

    try:
        base_members = Member.objects.all()
        if user.role == User.Roles.SUPER_ADMIN:
            members_qs = base_members
        elif user.is_broker_role and user.related_broker:
            members_qs = base_members.filter(client__broker=user.related_broker)
        elif user.is_hr_role and user.related_client:
            members_qs = base_members.filter(client=user.related_client)
        else:
            members_qs = base_members.none()

        member = members_qs.get(national_id=q)
    except Member.DoesNotExist:
        member = None

    return render(request, 'service_requests/partials/member_search_result.html', {
        'member': member, 'q': q
    })


# ==========================================
# إرسال الطلب (Member / HR)
# ==========================================
@login_required
@require_POST
def submit_request(request, pk):
    sreq = get_object_or_404(get_allowed_requests(request.user), pk=pk)
    try:
        with transaction.atomic():
            sreq.submit(user=request.user)
        messages.success(request, "تم إرسال الطلب بنجاح.")
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('service_requests:request_detail', pk=pk)


# ==========================================
# إجراءات الوسيط (Broker Actions)
# ==========================================
@login_required
@require_POST
def broker_start_review(request, pk):
    sreq = get_object_or_404(get_allowed_requests(request.user), pk=pk)
    try:
        with transaction.atomic():
            sreq.start_review(user=request.user)
        messages.success(request, "تم بدء مراجعة الطلب.")
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('service_requests:request_detail', pk=pk)


@login_required
@require_POST
def broker_return_request(request, pk):
    sreq = get_object_or_404(get_allowed_requests(request.user), pk=pk)
    note = request.POST.get('note', '').strip()
    if not note:
        messages.error(request, "يجب كتابة سبب لإعادة الطلب.")
        return redirect('service_requests:request_detail', pk=pk)

    try:
        with transaction.atomic():
            sreq.return_request(user=request.user, note=note)
        messages.success(request, "تم إعادة الطلب للعضو.")
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('service_requests:request_detail', pk=pk)


@login_required
@require_POST
def broker_resolve_request(request, pk):
    sreq = get_object_or_404(get_allowed_requests(request.user), pk=pk)
    note = request.POST.get('note', '').strip()

    try:
        with transaction.atomic():
            sreq.resolve(user=request.user, note=note)
        messages.success(request, "تم حل الطلب بنجاح.")
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('service_requests:request_detail', pk=pk)


@login_required
@require_POST
def broker_reject_request(request, pk):
    sreq = get_object_or_404(get_allowed_requests(request.user), pk=pk)
    note = request.POST.get('note', '').strip()
    if not note:
        messages.error(request, "يجب كتابة سبب لرفض الطلب.")
        return redirect('service_requests:request_detail', pk=pk)

    try:
        with transaction.atomic():
            sreq.reject(user=request.user, note=note)
        messages.error(request, "تم رفض الطلب.")
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('service_requests:request_detail', pk=pk)
