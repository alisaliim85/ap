from datetime import date
from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.contrib import messages
from django.utils.translation import gettext as _
from .models import MedicationRequest, MedicationRefill

def generate_medication_schedule(
    request, 
    med_request: MedicationRequest, 
    start_date: date, 
    partner_id: str = None
) -> int:
    """
    دالة توليد الجدولة مع مراعاة سقف الوثيقة التأمينية.
    """
    # الوصول لتاريخ نهاية الوثيقة عبر العلاقات المعمارية
    member = med_request.service_request.member
    policy_end_date = member.policy_class.policy.end_date
    
    total_cycles = med_request.total_duration_months // med_request.interval_months
    refills_to_create = []
    cycles_generated = 0
    
    for cycle in range(1, total_cycles + 1):
        months_to_add = (cycle - 1) * med_request.interval_months
        scheduled_date = start_date + relativedelta(months=+months_to_add)
        
        # الشرط المعماري: القطع المالي بناءً على الوثيقة
        if scheduled_date > policy_end_date:
            messages.warning(
                request, 
                _(f"تم إيقاف الجدولة عند الدورة {cycle} لأن الوثيقة التأمينية تنتهي في {policy_end_date}.")
            )
            break
            
        # الدورة الأولى تذهب للتجهيز فوراً، البقية تبقى في الانتظار
        initial_status = (
            MedicationRefill.RefillStatus.PROCESSING 
            if cycle == 1 
            else MedicationRefill.RefillStatus.PENDING
        )
        
        refill = MedicationRefill(
            medication_request=med_request,
            partner_id=partner_id,
            cycle_number=cycle,
            scheduled_date=scheduled_date,
            status=initial_status,
        )
        refills_to_create.append(refill)
        cycles_generated += 1
        
    if cycles_generated > 0:
        with transaction.atomic():
            MedicationRefill.objects.bulk_create(refills_to_create)
            med_request.status = MedicationRequest.Status.ACTIVE
            med_request.save(update_fields=['status'])
            
    return cycles_generated