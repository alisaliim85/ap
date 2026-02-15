import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinLengthValidator, MaxLengthValidator

class Member(models.Model):
    class Gender(models.TextChoices):
        MALE = 'M', _('Male')
        FEMALE = 'F', _('Female')

    class RelationType(models.TextChoices):
        PRINCIPAL = 'PRINCIPAL', _('Principal (Employee)')
        SPOUSE = 'SPOUSE', _('Spouse')
        CHILD = 'CHILD', _('Child (Son/Daughter)')
        PARENT = 'PARENT', _('Parent')
        BROTHER = 'BROTHER', _('Brother')
        SISTER = 'SISTER', _('Sister')
        OTHER = 'OTHER', _('Other')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 1. الشركة التابع لها العضو (للأداء والفلترة السريعة)
    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.CASCADE,
        related_name='members',
        verbose_name=_("Company / Client")
    )

    # 2. ربط اختياري مع جدول المستخدمين
    user = models.OneToOneField(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='member_profile',
        db_index=True
    )

    # 3. الفئة التأمينية
    policy_class = models.ForeignKey(
        'policies.PolicyClass',
        on_delete=models.PROTECT,
        related_name='members',
        db_index=True
    )

    # 4. الكفيل (رب الأسرة)
    sponsor = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='dependents',
        db_index=True
    )

    # البيانات الشخصية
    full_name = models.CharField(_("Full Name"), max_length=255)
    
    # الهوية والعنوان (مشفرة)
    national_id = models.CharField(
        _("National ID / Iqama"), 
        max_length=10, 
        unique=True,
        db_index=True,
        validators=[MinLengthValidator(10), MaxLengthValidator(10)],
    )
    
    national_address = models.TextField(
        _("National Address"),
        blank=True,
    )
    
    medical_card_number = models.CharField(_("Medical Card ID"), max_length=50, unique=True, null=True, blank=True)
    
    birth_date = models.DateField(_("Date of Birth"))
    gender = models.CharField(_("Gender"), max_length=1, choices=Gender.choices)
    relation = models.CharField(_("Relationship"), max_length=20, choices=RelationType.choices)
    
    phone_number = models.CharField(_("Mobile Number"), max_length=20)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Member / Beneficiary")
        verbose_name_plural = _("Members / Beneficiaries")
        indexes = [
            models.Index(fields=['medical_card_number']),
            models.Index(fields=['full_name']), # تسريع البحث بالاسم
        ]
        permissions = [
            ("view_all_members", "Can view members of their company"),
            ("manage_members", "Can add/edit members"),
            ("bulk_upload_members", "Can perform bulk upload"),
            ("view_my_family_members", "Can view their own family members"),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.client.name_en})"


class MemberDocument(models.Model):
    """
    مرفقات الأعضاء
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(_("Document Title"), max_length=100)
    file = models.FileField(upload_to='members/docs/%Y/%m/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title