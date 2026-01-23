from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # الأعمدة التي تظهر في القائمة
    list_display = ('username', 'first_name', 'last_name', 'role', 'get_link', 'is_active')
    list_filter = ('role', 'is_active', 'is_staff')
    
    # إضافة الحقول الجديدة إلى صفحة التعديل
    fieldsets = UserAdmin.fieldsets + (
        ('AP PLUS Info', {'fields': ('role', 'related_client', 'related_partner', 'national_id', 'phone_number')}),
    )
    
    # دالة مساعدة لعرض الجهة التابع لها المستخدم
    def get_link(self, obj):
        if obj.related_client:
            return f"Client: {obj.related_client.name_en}"
        elif obj.related_partner:
            return f"Partner: {obj.related_partner.name_en}"
        return "-"
    get_link.short_description = "Affiliation"