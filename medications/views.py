"""
Medications app — full view implementation.
"""
import shutil
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile

from service_requests.models import ServiceRequest, RequestAttachment
from .models import MedicationRequest, MedicationRefill, MedicationAttachment
from .forms import MedicationTransferForm, ScheduleRefillForm, RefillReviewForm
from .utils import (
    check_policy_active_on_date,
    get_member_policy_info,
    get_upcoming_refills,
    get_expiring_prescriptions,
)


# ---------------------------------------------------------------------------
# 1. Dashboard
# ---------------------------------------------------------------------------
@login_required
@permission_required('medications.can_view_medication_dashboard', raise_exception=True)
def medication_dashboard(request):
    qs = (
        MedicationRequest.objects
        .select_related('service_request', 'created_by')
        .order_by('-created_at')
    )

    search = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    if search:
        qs = qs.filter(reference__icontains=search)
    if status_filter:
        qs = qs.filter(status=status_filter)

    upcoming_refills = get_upcoming_refills(days=7)
    expiring_prescriptions = get_expiring_prescriptions(days=10)

    context = {
        'medication_requests': qs,
        'status_choices': MedicationRequest.Status.choices,
        'search': search,
        'status_filter': status_filter,
        'upcoming_refills': upcoming_refills,
        'expiring_prescriptions': expiring_prescriptions,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'medications/partials/medication_table.html', context)
    return render(request, 'medications/medication_dashboard.html', context)


# ---------------------------------------------------------------------------
# 2. Transfer service request → medications
# ---------------------------------------------------------------------------
@login_required
@permission_required('medications.can_transfer_to_medications', raise_exception=True)
def transfer_to_medications(request, service_request_id):
    sr = get_object_or_404(ServiceRequest, pk=service_request_id)

    # Guard: already transferred
    if hasattr(sr, 'medication_details'):
        if request.headers.get('HX-Request'):
            return HttpResponse(
                '<div class="alert alert-warning">تم النقل مسبقاً لهذا الطلب.</div>',
                content_type='text/html',
            )
        messages.warning(request, 'تم النقل مسبقاً لهذا الطلب.')
        return redirect('service_requests:service_request_detail', pk=sr.pk)

    form = MedicationTransferForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        cd = form.cleaned_data
        address_snapshot = {'address': cd.get('delivery_address', '')}

        med_req = MedicationRequest.objects.create(
            service_request=sr,
            prescription_date=cd['prescription_date'],
            prescription_validity_months=cd['prescription_validity_months'],
            interval_months=cd['interval_months'],
            total_duration_months=cd['total_duration_months'],
            delivery_address_snapshot=address_snapshot,
            broker_note=cd.get('broker_note', ''),
            created_by=request.user,
        )

        # Copy attachments from the service request
        for att in sr.attachments.all():
            try:
                att.file.open('rb')
                content = att.file.read()
                att.file.close()
                import os
                filename = os.path.basename(att.file.name)
                new_att = MedicationAttachment(
                    medication_request=med_req,
                    original_attachment=att,
                    description=att.description,
                )
                new_att.file.save(filename, ContentFile(content), save=True)
            except Exception:
                pass  # If file copy fails, skip gracefully

        # Update service request status
        try:
            sr.change_status(
                new_status=ServiceRequest.Status.TRANSFERRED_TO_MEDICATIONS,
                user=request.user,
                action='transfer_to_medications',
                note='تم نقل الطلب إلى وحدة الأدوية.',
            )
        except Exception:
            sr.status = ServiceRequest.Status.TRANSFERRED_TO_MEDICATIONS
            sr.save(update_fields=['status'])

        messages.success(request, f'تم نقل الطلب بنجاح. المرجع: {med_req.reference}')

        if request.headers.get('HX-Request'):
            response = HttpResponse(status=204)
            response['HX-Redirect'] = med_req.get_absolute_url() if hasattr(med_req, 'get_absolute_url') else '/'
            return response
        return redirect('medications:medication_detail', medication_request_id=med_req.pk)

    context = {'form': form, 'service_request': sr}
    if request.headers.get('HX-Request'):
        return render(request, 'medications/partials/transfer_form.html', context)
    return render(request, 'medications/partials/transfer_form.html', context)


# ---------------------------------------------------------------------------
# 3. Schedule a refill
# ---------------------------------------------------------------------------
@login_required
@permission_required('medications.can_schedule_refill', raise_exception=True)
def schedule_refill(request, medication_request_id):
    med_req = get_object_or_404(MedicationRequest, pk=medication_request_id)
    form = ScheduleRefillForm(request.POST or None)

    # Compute next cycle number
    existing_cycles = med_req.refills.values_list('cycle_number', flat=True)
    next_cycle = max(existing_cycles, default=0) + 1
    max_cycles = med_req.max_cycles

    # Policy check
    policy_status = None
    if request.method == 'GET' and form.is_bound is False:
        import datetime
        policy_status = check_policy_active_on_date(
            med_req.service_request.member if hasattr(med_req.service_request, 'member') else None,
            datetime.date.today(),
        ) if hasattr(med_req.service_request, 'member') else None

    if request.method == 'POST' and form.is_valid():
        if next_cycle > max_cycles:
            messages.error(request, f'تم الوصول للحد الأقصى من الدورات ({max_cycles}).')
        else:
            refill = form.save(commit=False)
            refill.medication_request = med_req
            refill.cycle_number = next_cycle
            refill.scheduled_by = request.user
            refill.save()

            messages.success(request, f'تم جدولة الدورة #{next_cycle} بنجاح.')
            if request.headers.get('HX-Request'):
                response = HttpResponse(status=204)
                response['HX-Refresh'] = 'true'
                return response
            return redirect('medications:medication_detail', medication_request_id=med_req.pk)

    context = {
        'form': form,
        'medication_request': med_req,
        'next_cycle': next_cycle,
        'max_cycles': max_cycles,
        'policy_status': policy_status,
    }
    if request.headers.get('HX-Request'):
        return render(request, 'medications/partials/schedule_form.html', context)
    return render(request, 'medications/partials/schedule_form.html', context)


# ---------------------------------------------------------------------------
# 4. Review / approve refill
# ---------------------------------------------------------------------------
@login_required
@permission_required('medications.can_approve_refill', raise_exception=True)
def review_refill(request, refill_id):
    refill = get_object_or_404(MedicationRefill, pk=refill_id)
    form = RefillReviewForm(request.POST or None)

    policy_status = None
    try:
        member = refill.medication_request.service_request.member
        policy_status = check_policy_active_on_date(member, refill.scheduled_date)
    except Exception:
        pass

    if request.method == 'POST' and form.is_valid():
        action = form.cleaned_data['action']
        notes = form.cleaned_data.get('notes', '')
        try:
            if action == RefillReviewForm.ACTION_APPROVE:
                refill.change_status(
                    MedicationRefill.RefillStatus.APPROVED,
                    user=request.user,
                    action_name='approve_refill',
                    reason=notes,
                )
                messages.success(request, 'تمت الموافقة على دورة الصرف.')
            elif action == RefillReviewForm.ACTION_CANCEL:
                refill.change_status(
                    MedicationRefill.RefillStatus.CANCELLED,
                    user=request.user,
                    action_name='cancel_refill',
                    reason=notes,
                )
                messages.warning(request, 'تم إلغاء دورة الصرف.')
        except ValidationError as e:
            messages.error(request, str(e))

        if request.headers.get('HX-Request'):
            response = HttpResponse(status=204)
            response['HX-Refresh'] = 'true'
            return response
        return redirect('medications:medication_detail', medication_request_id=refill.medication_request.pk)

    context = {'form': form, 'refill': refill, 'policy_status': policy_status}
    if request.headers.get('HX-Request'):
        return render(request, 'medications/partials/review_form.html', context)
    return render(request, 'medications/partials/review_form.html', context)


# ---------------------------------------------------------------------------
# 5. Medication request detail
# ---------------------------------------------------------------------------
@login_required
def medication_detail(request, medication_request_id):
    med_req = get_object_or_404(
        MedicationRequest.objects.select_related('service_request', 'created_by'),
        pk=medication_request_id,
    )
    refills = med_req.refills.select_related('partner', 'scheduled_by', 'approved_by').order_by('cycle_number')
    attachments = med_req.attachments.all()
    comments = med_req.comments.select_related('author').order_by('created_at')
    status_logs = med_req.status_logs.select_related('user').order_by('-created_at')

    context = {
        'medication_request': med_req,
        'refills': refills,
        'attachments': attachments,
        'comments': comments,
        'status_logs': status_logs,
        'schedule_form': ScheduleRefillForm(),
    }
    return render(request, 'medications/medication_detail.html', context)


# ---------------------------------------------------------------------------
# 5b. Change medication request status (activate / complete / cancel)
# ---------------------------------------------------------------------------
@login_required
@permission_required('medications.can_view_medication_dashboard', raise_exception=True)
@require_POST
def change_medication_status(request, medication_request_id):
    med_req = get_object_or_404(MedicationRequest, pk=medication_request_id)
    new_status = request.POST.get('new_status', '').strip()
    note = request.POST.get('note', '').strip()

    valid_statuses = [s.value for s in MedicationRequest.Status]
    if new_status not in valid_statuses:
        messages.error(request, 'حالة غير صالحة.')
        return redirect('medications:medication_detail', medication_request_id=med_req.pk)

    try:
        med_req.change_status(
            new_status=new_status,
            user=request.user,
            action=f'change_status_to_{new_status.lower()}',
            note=note,
        )
        status_labels = {
            'ACTIVE': 'تم تفعيل طلب الأدوية.',
            'COMPLETED': 'تم إكمال طلب الأدوية.',
            'CANCELLED': 'تم إلغاء طلب الأدوية.',
        }
        messages.success(request, status_labels.get(new_status, 'تم تحديث الحالة.'))
    except ValidationError as e:
        messages.error(request, str(e))

    return redirect('medications:medication_detail', medication_request_id=med_req.pk)


# ---------------------------------------------------------------------------
# 6. Pharmacy: list of approved refills
# ---------------------------------------------------------------------------
@login_required
@permission_required('medications.can_dispense_medication', raise_exception=True)
def pharmacy_refill_list(request):
    user = request.user

    qs = (
        MedicationRefill.objects
        .exclude(status__in=[MedicationRefill.RefillStatus.DELIVERED, MedicationRefill.RefillStatus.CANCELLED])
        .select_related('medication_request', 'partner')
        .order_by('scheduled_date')
    )

    # Filter by user's related partner unless superuser
    if not user.is_superuser and hasattr(user, 'related_partner') and user.related_partner:
        qs = qs.filter(partner=user.related_partner)

    search = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    if search:
        qs = qs.filter(medication_request__reference__icontains=search)
    if status_filter:
        qs = qs.filter(status=status_filter)

    context = {
        'refills': qs,
        'search': search,
        'status_filter': status_filter,
        'status_choices': MedicationRefill.RefillStatus.choices,
    }
    if request.headers.get('HX-Request'):
        return render(request, 'medications/partials/pharmacy_refill_table.html', context)
    return render(request, 'medications/pharmacy_list.html', context)


# ---------------------------------------------------------------------------
# 7. Pharmacy: refill detail
# ---------------------------------------------------------------------------
@login_required
@permission_required('medications.can_dispense_medication', raise_exception=True)
def pharmacy_refill_detail(request, refill_id):
    refill = get_object_or_404(
        MedicationRefill.objects.select_related(
            'medication_request', 'partner', 'scheduled_by', 'approved_by'
        ),
        pk=refill_id,
    )

    # Guard: pharmacist can only see their own pharmacy's refills
    user = request.user
    if (
        not user.is_superuser
        and hasattr(user, 'related_partner')
        and user.related_partner
        and refill.partner != user.related_partner
    ):
        messages.error(request, 'ليس لديك صلاحية عرض هذا الطلب.')
        return redirect('medications:pharmacy_refill_list')

    # Member policy info
    policy_info = None
    try:
        member = refill.medication_request.service_request.member
        policy_info = get_member_policy_info(member)
    except Exception:
        pass

    status_logs = refill.status_logs.select_related('user').order_by('-created_at')
    attachments = refill.medication_request.attachments.all()

    context = {
        'refill': refill,
        'policy_info': policy_info,
        'status_logs': status_logs,
        'attachments': attachments,
        'allowed_transitions': _get_allowed_transitions(refill),
    }
    return render(request, 'medications/pharmacy_detail.html', context)


_TRANSITION_META = {
    MedicationRefill.RefillStatus.PROCESSING: {
        'label': 'بدء التجهيز',
        'icon': 'ph-gear',
        'btn_class': 'bg-amber-600 text-white hover:bg-amber-700',
    },
    MedicationRefill.RefillStatus.OUT_FOR_DELIVERY: {
        'label': 'خرج للتوصيل',
        'icon': 'ph-truck',
        'btn_class': 'bg-blue-600 text-white hover:bg-blue-700',
    },
    MedicationRefill.RefillStatus.DELIVERED: {
        'label': 'تأكيد التسليم',
        'icon': 'ph-package-check',
        'btn_class': 'bg-green-600 text-white hover:bg-green-700',
    },
    MedicationRefill.RefillStatus.CANCELLED: {
        'label': 'إلغاء الدورة',
        'icon': 'ph-x-circle',
        'btn_class': 'bg-red-50 text-red-700 border border-red-200 hover:bg-red-100',
    },
}

def _get_allowed_transitions(refill):
    _map = {
        MedicationRefill.RefillStatus.APPROVED:  [MedicationRefill.RefillStatus.PROCESSING, MedicationRefill.RefillStatus.CANCELLED],
        MedicationRefill.RefillStatus.PROCESSING: [MedicationRefill.RefillStatus.OUT_FOR_DELIVERY, MedicationRefill.RefillStatus.CANCELLED],
        MedicationRefill.RefillStatus.OUT_FOR_DELIVERY: [MedicationRefill.RefillStatus.DELIVERED, MedicationRefill.RefillStatus.CANCELLED],
    }
    result = []
    for status in _map.get(refill.status, []):
        meta = _TRANSITION_META.get(status, {})
        result.append({'status': status, **meta})
    return result


# ---------------------------------------------------------------------------
# 8. Update refill status (pharmacy action)
# ---------------------------------------------------------------------------
@login_required
@permission_required('medications.can_dispense_medication', raise_exception=True)
@require_POST
def update_refill_status(request, refill_id):
    refill = get_object_or_404(MedicationRefill, pk=refill_id)
    user = request.user

    # Guard: pharmacist can only act on their own pharmacy's refills
    if (
        not user.is_superuser
        and hasattr(user, 'related_partner')
        and user.related_partner
        and refill.partner != user.related_partner
    ):
        messages.error(request, 'ليس لديك صلاحية تحديث هذا الطلب.')
        return redirect('medications:pharmacy_refill_list')

    new_status = request.POST.get('new_status', '').strip()
    reason = request.POST.get('reason', '').strip()

    if not new_status:
        messages.error(request, 'يرجى تحديد الحالة الجديدة.')
    else:
        try:
            refill.change_status(
                new_status=new_status,
                user=user,
                action_name='pharmacy_update',
                reason=reason,
            )
            messages.success(request, 'تم تحديث حالة الدورة بنجاح.')
        except ValidationError as e:
            messages.error(request, str(e))

    if request.headers.get('HX-Request'):
        return render(request, 'medications/partials/refill_row.html', {'refill': refill})
    return redirect('medications:pharmacy_refill_detail', refill_id=refill.pk)

