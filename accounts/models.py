import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from encrypted_model_fields.fields import EncryptedCharField

class User(AbstractUser):
    """
    نظام المستخدم الموحد: يدعم موظفي الوسيط، العملاء، والشركاء
    """
    
    class Roles(models.TextChoices):
        # 1. فريق الوسيط (AP PLUS)
        BROKER_ADMIN = 'BROKER_ADMIN', _('Broker Admin (Super)')
        BROKER_STAFF = 'BROKER_STAFF', _('Broker Staff')
        
        # 2. فريق العملاء (مثل SBG)
        HR_ADMIN = 'HR_ADMIN', _('HR Admin')
        HR_STAFF = 'HR_STAFF', _('HR Staff')
        
        # 3. فريق الشركاء (الصيدليات والمراكز)
        PHARMACIST = 'PHARMACIST', _('Pharmacist')
        CHRONIC_ADMIN = 'CHRONIC_ADMIN', _('Chronic Disease Admin')
        CHRONIC_STAFF = 'CHRONIC_STAFF', _('Chronic Disease Staff')
        
        # 4. عام
        VIEWER = 'VIEWER', _('Viewer / Auditor')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    role = models.CharField(
        _("Role"), 
        max_length=50, 
        choices=Roles.choices, 
        default=Roles.VIEWER
    )

    # --- علاقات التبعية (لمن يتبع هذا المستخدم؟) ---

    # 1. لموظفي الـ HR (يتبعون لعميل محدد)
    related_client = models.ForeignKey(
        'clients.Client', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='users',
        verbose_name=_("Related Company (For HR)")
    )

    # 2. للصيادلة وأطباء الأمراض المزمنة (يتبعون لشريك محدد)
    related_partner = models.ForeignKey(
        'partners.Partner',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name=_("Related Partner (For Pharmacists/Doctors)")
    )

    # بيانات حساسة مشفرة
    national_id = EncryptedCharField(
        _("National ID"), 
        max_length=20, 
        blank=True, 
        help_text=_("Encrypted in Database")
    )
    
    phone_number = models.CharField(_("Phone Number"), max_length=20, blank=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    # --- دوال مساعدة للتحقق من الصلاحيات في القوالب ---
    @property
    def is_broker(self):
        return self.role in [self.Roles.BROKER_ADMIN, self.Roles.BROKER_STAFF]

    @property
    def is_hr(self):
        return self.role in [self.Roles.HR_ADMIN, self.Roles.HR_STAFF]
        
    @property
    def is_partner(self):
        return self.role in [self.Roles.PHARMACIST, self.Roles.CHRONIC_ADMIN, self.Roles.CHRONIC_STAFF]