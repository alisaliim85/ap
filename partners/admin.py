from django.contrib import admin
from .models import Partner

@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ('name_en', 'partner_type', 'contact_person', 'email', 'is_active')
    list_filter = ('partner_type', 'is_active')
    search_fields = ('name_en', 'commercial_record')