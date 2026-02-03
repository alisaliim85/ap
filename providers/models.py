import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _

class Provider(models.Model):
    """
    يمثل شركة التأمين (Insurance Company)
    مثال: NCCI, Bupa, Malath
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name_ar = models.CharField(_("Arabic Name"), max_length=255)
    name_en = models.CharField(_("English Name"), max_length=255)
    
    # رقم ترخيص هيئة التأمين (مهم للربط المستقبلي)
    license_number = models.CharField(_("License Number"), max_length=50, unique=True)
    
    # تفاصيل التواصل الخاصة بالمطالبات
    claim_email = models.EmailField(_("Claims Email"), blank=True)
    website = models.URLField(_("Website"), blank=True)
    
    logo = models.ImageField(upload_to='providers/logos/', blank=True, null=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Insurance Provider")
        verbose_name_plural = _("Insurance Providers")
        ordering = ['name_en']
        permissions = [
            ("manage_insurance_companies", "Can create/edit insurance companies"),
        ]

    def __str__(self):
        return f"{self.name_en} ({self.name_ar})"