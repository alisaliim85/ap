"""
Utility functions for the medications app.
- Policy validation
- Member insurance info
- Upcoming refill/prescription alerts
"""
import datetime
from .models import MedicationRequest, MedicationRefill


def check_policy_active_on_date(member, target_date):
    """
    Check whether the member's policy is active on a given date.
    Returns a dict: {is_valid, policy, expiry_date, days_remaining, message}
    """
    try:
        policy_class = member.policy_class
        policy = policy_class.policy
    except Exception:
        return {
            'is_valid': False,
            'policy': None,
            'expiry_date': None,
            'days_remaining': None,
            'message': 'لا توجد وثيقة مرتبطة بالمستفيد.',
        }

    if not policy.is_active:
        return {
            'is_valid': False,
            'policy': policy,
            'expiry_date': policy.end_date,
            'days_remaining': 0,
            'message': 'الوثيقة غير فعّالة.',
        }

    if target_date < policy.start_date:
        return {
            'is_valid': False,
            'policy': policy,
            'expiry_date': policy.end_date,
            'days_remaining': 0,
            'message': 'تاريخ الصرف قبل بدء سريان الوثيقة.',
        }

    if target_date > policy.end_date:
        return {
            'is_valid': False,
            'policy': policy,
            'expiry_date': policy.end_date,
            'days_remaining': 0,
            'message': 'انتهت صلاحية الوثيقة التأمينية.',
        }

    days_remaining = (policy.end_date - target_date).days
    return {
        'is_valid': True,
        'policy': policy,
        'expiry_date': policy.end_date,
        'days_remaining': days_remaining,
        'message': f'الوثيقة سارية لمدة {days_remaining} يوم.',
    }


def get_member_policy_info(member):
    """
    Returns a summary dict of the member's current insurance policy.
    """
    try:
        policy_class = member.policy_class
        policy = policy_class.policy
        client = policy.client
    except Exception:
        return None

    today = datetime.date.today()
    is_active = policy.is_active and policy.start_date <= today <= policy.end_date

    return {
        'policy_number': policy.policy_number,
        'start_date': policy.start_date,
        'end_date': policy.end_date,
        'class_name': policy_class.name,
        'relation': member.get_relation_display(),
        'membership_number': member.medical_card_number,
        'insurance_company': client.name_ar if hasattr(client, 'name_ar') else str(client),
        'is_active': is_active,
    }


def get_upcoming_refills(days=7):
    """
    Returns refills with status PENDING or APPROVED scheduled within the next `days` days
    and whose parent MedicationRequest is ACTIVE.
    """
    today = datetime.date.today()
    cutoff = today + datetime.timedelta(days=days)
    return (
        MedicationRefill.objects
        .filter(
            status__in=[MedicationRefill.RefillStatus.PENDING, MedicationRefill.RefillStatus.APPROVED],
            scheduled_date__range=(today, cutoff),
            medication_request__status=MedicationRequest.Status.ACTIVE,
        )
        .select_related('medication_request', 'partner')
        .order_by('scheduled_date')
    )


def get_expiring_prescriptions(days=10):
    """
    Returns ACTIVE MedicationRequests whose prescription will expire within `days` days.
    """
    today = datetime.date.today()
    results = []
    qs = (
        MedicationRequest.objects
        .filter(status=MedicationRequest.Status.ACTIVE)
        .select_related('service_request')
    )
    for mr in qs:
        expiry = mr.prescription_expiry_date
        diff = (expiry - today).days
        if 0 <= diff <= days:
            results.append(mr)
    return results
