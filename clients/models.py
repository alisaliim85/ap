import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def default_services_config():
    return {
        "claims": {
            "bypass_hr_review": False,
        }
    }

class Client(models.Model):
    """
    يمثل هذا الجدول الشركات أو المؤسسات المتعاقدة (مثل SBG).
    يدعم الهيكلة الشجرية (شركة قابضة تحتها شركات تابعة)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Self-referencing ForeignKey for Holding Company logic
    # إذا كان الحقل فارغاً، فهذا يعني أنها شركة قابضة أو مستقلة
    # إذا تم اختيار شركة، فهذا يعني أن هذه الشركة تابعة للشركة المختارة
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='subsidiaries',
        verbose_name=_("Parent Company (Holding)")
    )
    
    name_ar = models.CharField(_("Arabic Name"), max_length=255)
    name_en = models.CharField(_("English Name"), max_length=255)
    commercial_record = models.CharField(_("Commercial Record"), max_length=50, unique=True)
    broker = models.ForeignKey(
        'brokers.Broker',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clients',
        verbose_name=_("Broker")
    )
    
    # تفاصيل الاتصال
    email = models.EmailField(_("Contact Email"), blank=True)
    phone = models.CharField(_("Phone Number"), max_length=20, blank=True)

    services_config = models.JSONField(
        _("Services Configuration"),
        default=default_services_config,
        blank=True, # يسمح بأن يكون فارغاً في الأدمن
        help_text=_("JSON configuration for various services (e.g., claims workflow settings).")
    )
    
    require_hr_review = models.BooleanField(
        _("Require HR Review for Service Requests"),
        default=False,
        help_text=_("If enabled, service requests submitted by members will be reviewed by HR before being forwarded to the broker.")
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Client / Company")
        verbose_name_plural = _("Clients / Companies")
        ordering = ['name_en']
        permissions = [
            ("manage_clients", "Can create/edit clients"),
            ("view_client_dashboard", "Can view client dashboard statistics"),
            
        ]

    def __str__(self):
        # يعرض اسم الشركة، ولو كانت فرعية يوضح ذلك
        if self.parent:
            return f"{self.name_en} (Sub of {self.parent.name_en})"
        return self.name_en

    @property
    def is_holding(self):
        return self.subsidiaries.exists()

    def get_claim_setting(self, setting_name, default=False):
        """
        جلب إعداد محدد لقسم المطالبات من services_config.
        """
        if not self.services_config or 'claims' not in self.services_config:
            return default
        return self.services_config['claims'].get(setting_name, default)


def get_group_root(client):
    """
    إرجاع جذر مجموعة القابضة (أعلى أب في سلسلة parent).
    إذا لم يكن للعميل أب، يعيد العميل نفسه.
    """
    current = client
    while current.parent_id:
        current = current.parent
    return current


class SponsorNumber(models.Model):
    """
    رقم كفيل (معرّف المنشأة في أبشر/مقيم) — كيان مشترك داخل مجموعة القابضة.
    يمكن أن يغطي موظفين من عدة شركات شقيقة، وله شركة مالكة واحدة،
    وكل رقم كفيل يخص مجموعة قابضة واحدة فقط.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # جذر مجموعة القابضة (يحدد المجموعة الواحدة التي ينتمي لها الرقم)
    group = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='sponsor_numbers',
        verbose_name=_("Holding Group"),
    )
    # الشركة المالكة للكفيل (ضمن نفس المجموعة)
    owner_client = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,
        related_name='owned_sponsor_numbers',
        verbose_name=_("Owner Company"),
    )

    sponsor_number = models.CharField(_("Sponsor Number (Establishment ID)"), max_length=50)
    name = models.CharField(_("Name"), max_length=150, blank=True)
    is_active = models.BooleanField(_("Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Sponsor Number")
        verbose_name_plural = _("Sponsor Numbers")
        ordering = ['sponsor_number']
        # الرقم يخص مجموعة قابضة واحدة فقط
        unique_together = ('group', 'sponsor_number')

    def clean(self):
        # الشركة المالكة يجب أن تكون ضمن نفس مجموعة القابضة
        if self.owner_client_id:
            if get_group_root(self.owner_client) != self.group:
                raise ValidationError(
                    _("The owner company must belong to the same holding group as the sponsor number.")
                )

    def save(self, *args, **kwargs):
        # ملء المجموعة تلقائياً من جذر الشركة المالكة (إن لم تُحدد)
        if not self.group_id and self.owner_client_id:
            self.group = get_group_root(self.owner_client)
        super().save(*args, **kwargs)

    def __str__(self):
        owner = self.owner_client.name_en if self.owner_client_id else '-'
        return f"{self.sponsor_number} ({owner})"