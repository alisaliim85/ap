from django.contrib import admin
from .models import Provider

@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ('name_en', 'license_number', 'claim_email', 'is_active')
    search_fields = ('name_en', 'license_number')