from django.db import models
import uuid
from django.utils.translation import gettext_lazy as _

class Broker(models.Model):
    """
    شركات الوساطة المستأجرة للنظام (SaaS Tenants)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name_ar = models.CharField(_("Arabic Name"), max_length=255)
    name_en = models.CharField(_("English Name"), max_length=255)
    commercial_record = models.CharField(_("Commercial Record"), max_length=50, unique=True)
    
    logo = models.ImageField(_("Broker Logo"), upload_to='brokers/logos/', null=True, blank=True)
    
    is_active = models.BooleanField(_("Is Active"), default=True) 
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Broker")
        verbose_name_plural = _("Brokers")

    def __str__(self):
        return self.name_en


class BrokerSubscription(models.Model):
    """
    إدارة اشتراكات الوسطاء مع مالك المنصة
    """
    class PlanTypes(models.TextChoices):
        BASIC = 'BASIC', _('Basic Plan')
        PRO = 'PRO', _('Professional Plan')
        ENTERPRISE = 'ENTERPRISE', _('Enterprise Plan')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    broker = models.ForeignKey(Broker, on_delete=models.CASCADE, related_name='subscriptions')
    
    plan = models.CharField(_("Subscription Plan"), max_length=50, choices=PlanTypes.choices)
    platform_contract_file = models.FileField(upload_to='platform_contracts/', blank=True, null=True)
    
    start_date = models.DateField(_("Start Date"))
    end_date = models.DateField(_("End Date"))
    is_active = models.BooleanField(_("Is Active Subscription"), default=True)
    max_clients = models.IntegerField(_("Max Allowed Clients"), default=10)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Broker Subscription")
        verbose_name_plural = _("Broker Subscriptions")

    def __str__(self):
        return f"{self.broker.name_en} - {self.get_plan_display()}"


class BrokerPartnerContract(models.Model):
    """
    العقود التي تربط الوسيط بالشركاء (الصيدليات والمستشفيات)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    broker = models.ForeignKey(Broker, on_delete=models.CASCADE, related_name='partner_contracts')
    partner = models.ForeignKey('partners.Partner', on_delete=models.CASCADE, related_name='broker_contracts')
    
    contract_file = models.FileField(upload_to='contracts/broker_partner/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    commission_rate = models.DecimalField(_("Discount/Commission Rate"), max_digits=5, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('broker', 'partner')
        verbose_name = _("Broker-Partner Contract")
        verbose_name_plural = _("Broker-Partner Contracts")

    def __str__(self):
        return f"{self.broker.name_en} <-> {self.partner.name_en}"