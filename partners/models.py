import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _

class Partner(models.Model):
    """
    الشركاء الاستراتيجيين (شركات الصيدليات، مراكز إدارة الأمراض المزمنة)
    """
    class PartnerType(models.TextChoices):
        PHARMACY_CHAIN = 'PHARMACY_CHAIN', _('Pharmacy Chain')
        CHRONIC_CENTER = 'CHRONIC_CENTER', _('Chronic Care Center')
        OPTICAL_CHAIN = 'OPTICAL_CHAIN', _('Optical Chain')
        OTHER = 'OTHER', _('Other')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name_ar = models.CharField(_("Name (AR)"), max_length=255)
    name_en = models.CharField(_("Name (EN)"), max_length=255)
    
    partner_type = models.CharField(_("Partner Type"), max_length=50, choices=PartnerType.choices)
    
    # السجل التجاري
    commercial_record = models.CharField(_("Commercial Record"), max_length=50, unique=True)
    
    # تفاصيل المدير المسؤول لدى الشريك (للتواصل)
    contact_person = models.CharField(_("Contact Person"), max_length=100)
    email = models.EmailField(_("Email"))
    phone = models.CharField(_("Phone"), max_length=20)
    
    # العقد الموقع مع الوسيط
    contract_file = models.FileField(upload_to='partners/contracts/', blank=True, null=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Partner Company")
        verbose_name_plural = _("Partner Companies")
        permissions = [
            ("manage_partners", "Can create/edit partners"),
            ("view_partner_contracts", "Can view/download sensitive contract files"),
        ]

    def __str__(self):
        return f"{self.name_en} ({self.get_partner_type_display()})"