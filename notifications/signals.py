# notifications/signals.py
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from service_requests.models import ServiceRequest
from claims.models import Claim
from .services import NotificationService


# ── ServiceRequest Signals ──────────────────────────────────────────────────

@receiver(pre_save, sender=ServiceRequest)
def sr_capture_old_status(sender, instance, **kwargs):
    """
    Store the current DB status on the instance before saving.
    post_save handler uses _original_status to detect actual changes.
    """
    if instance.pk:
        try:
            old = ServiceRequest.objects.get(pk=instance.pk)
            instance._original_status = old.status
        except ServiceRequest.DoesNotExist:
            instance._original_status = None
    else:
        instance._original_status = None


@receiver(post_save, sender=ServiceRequest)
def sr_notify_on_status_change(sender, instance, created, **kwargs):
    """
    Fire notification if status actually changed.
    """
    if created:
        return
    old_status = getattr(instance, '_original_status', None)
    new_status = instance.status
    if old_status is None or old_status == new_status:
        return

    fresh = ServiceRequest.objects.select_related(
        'member__client', 'member__user'
    ).get(pk=instance.pk)
    NotificationService.notify_service_request_status_change(fresh, old_status, new_status)


# ── Claim Signals ───────────────────────────────────────────────────────────

@receiver(pre_save, sender=Claim)
def claim_capture_old_status(sender, instance, **kwargs):
    """
    Same pattern as ServiceRequest — capture status before FSM transition saves.
    """
    if instance.pk:
        try:
            old = Claim.objects.get(pk=instance.pk)
            instance._original_status = old.status
        except Claim.DoesNotExist:
            instance._original_status = None
    else:
        instance._original_status = None


@receiver(post_save, sender=Claim)
def claim_notify_on_status_change(sender, instance, created, **kwargs):
    """
    Fire notification when Claim status transitions via FSM.
    """
    if created:
        return
    old_status = getattr(instance, '_original_status', None)
    new_status = instance.status
    if old_status is None or old_status == new_status:
        return

    fresh = Claim.objects.select_related(
        'member__client', 'member__user'
    ).get(pk=instance.pk)
    NotificationService.notify_claim_status_change(fresh, old_status, new_status)
