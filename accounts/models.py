import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    نظام المستخدم الموحد: يدعم موظفي الوسيط، العملاء، والشركاء
    """
    
    class Roles(models.TextChoices):
        # 0. مدير النظام (المطور/المالك)
        SUPER_ADMIN = 'SUPER_ADMIN', _('Super Admin (Owner)')
        # 1. فريق الوسيط (AP PLUS)
        BROKER_ADMIN = 'BROKER_ADMIN', _('Broker Admin')
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

        MEMBER = 'MEMBER', _('Member / Beneficiary')

    class Meta:
        permissions = [
            ("view_broker_dashboard", "Can view Broker Dashboard"),
            ("view_hr_dashboard", "Can view HR Dashboard"),
            ("view_partner_dashboard", "Can view Partner Dashboard"),
            ("view_member_dashboard", "Can view Member Dashboard"),
            ("manage_users", "Can manage system users"),
        ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    role = models.CharField(
        _("Role"), 
        max_length=50, 
        choices=Roles.choices, 
        default=Roles.MEMBER
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
    national_id = models.CharField(
        _("National ID"), 
        max_length=10, 
        blank=True,
        unique=True,
        db_index=True
    )
    
    phone_number = models.CharField(_("Phone Number"), max_length=20, blank=True)

    def save(self, *args, **kwargs):
        # إذا تم إنشاء المستخدم كـ superuser (مثلاً عبر سطر الأوامر)، نحدث دوره تلقائياً
        if self.is_superuser:
            self.role = self.Roles.SUPER_ADMIN

        # 1. السوبر أدمن (أنت فقط)
        if self.role == self.Roles.SUPER_ADMIN:
            self.is_superuser = True
            self.is_staff = True
        
        # 2. موظفو الوسيط (يدخلون الأدمن لكن ليسوا سوبر)
        elif self.role in [self.Roles.BROKER_ADMIN, self.Roles.BROKER_STAFF]:
            self.is_superuser = False # سحب الصلاحية المطلقة منهم
            self.is_staff = True      # السماح بدخول لوحة التحكم
            
        # 3. باقي المستخدمين (لا يدخلون لوحة تحكم دجانغو الافتراضية)
        else:
            self.is_superuser = False
            self.is_staff = False
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    # --- دوال مساعدة للتحقق من الصلاحيات في القوالب ---
    @property
    def is_broker(self):
        return self.has_perm('accounts.view_broker_dashboard')

    @property
    def is_hr(self):
        return self.has_perm('accounts.view_hr_dashboard')
        
    @property
    def is_partner(self):
        return self.has_perm('accounts.view_partner_dashboard')

    @property
    def is_member(self):
        return self.has_perm('accounts.view_member_dashboard')
