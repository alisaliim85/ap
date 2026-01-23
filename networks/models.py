import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _

# 1. مقدم الخدمة الطبية (المستشفى نفسه)
class ServiceProvider(models.Model):
    class ProviderTypes(models.TextChoices):
        HOSPITAL = 'HOSPITAL', _('Hospital')
        POLYCLINIC = 'POLYCLINIC', _('Polyclinic')
        PHARMACY = 'PHARMACY', _('Pharmacy')
        OPTICAL = 'OPTICAL', _('Optical Shop')
        LAB = 'LAB', _('Laboratory')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name_ar = models.CharField(_("Name (AR)"), max_length=255)
    name_en = models.CharField(_("Name (EN)"), max_length=255)
    
    type = models.CharField(_("Type"), max_length=20, choices=ProviderTypes.choices)
    city = models.CharField(_("City"), max_length=100)
    address = models.TextField(_("Address"), blank=True)
    
    # الإحداثيات للخريطة في تطبيق Flutter لاحقاً
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        verbose_name = _("Medical Service Provider")
        verbose_name_plural = _("Medical Service Providers")

    def __str__(self):
        return f"{self.name_en} - {self.city}"


# 2. الشبكة الطبية (التي تجمع المستشفيات)
class Network(models.Model):
    """
    الشبكة تتبع شركة تأمين معينة.
    مثال: شركة بوبا لديها شبكة "الماسية" وشبكة "البرونزية".
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # الربط بشركة التأمين
    provider = models.ForeignKey(
        'providers.Provider', 
        on_delete=models.CASCADE, 
        related_name='networks'
    )
    
    name_ar = models.CharField(_("Network Name (AR)"), max_length=100)
    name_en = models.CharField(_("Network Name (EN)"), max_length=100)
    
    # العلاقة Many-to-Many
    # الشبكة الواحدة تحتوي على مئات المستشفيات
    hospitals = models.ManyToManyField(
        ServiceProvider, 
        related_name='networks', 
        blank=True,
        verbose_name=_("Included Hospitals")
    )

    class Meta:
        verbose_name = _("Medical Network")
        verbose_name_plural = _("Medical Networks")
        unique_together = ('provider', 'name_en') # منع تكرار اسم الشبكة لنفس الشركة

    def __str__(self):
        return f"{self.name_en} ({self.provider.name_en})"