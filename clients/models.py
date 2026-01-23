import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _

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
    
    # تفاصيل الاتصال
    email = models.EmailField(_("Contact Email"), blank=True)
    phone = models.CharField(_("Phone Number"), max_length=20, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Client / Company")
        verbose_name_plural = _("Clients / Companies")
        ordering = ['name_en']

    def __str__(self):
        # يعرض اسم الشركة، ولو كانت فرعية يوضح ذلك
        if self.parent:
            return f"{self.name_en} (Sub of {self.parent.name_en})"
        return self.name_en