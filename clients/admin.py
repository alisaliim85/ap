from django.contrib import admin
from .models import Client, SponsorNumber

class SponsorNumberInline(admin.TabularInline):
    model = SponsorNumber
    extra = 0
    fk_name = 'owner_client'
    fields = ('sponsor_number', 'name', 'is_active')

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name_en', 'name_ar', 'parent', 'commercial_record', 'is_active')
    search_fields = ('name_en', 'name_ar', 'commercial_record')
    list_filter = ('is_active',)
    inlines = [SponsorNumberInline]

@admin.register(SponsorNumber)
class SponsorNumberAdmin(admin.ModelAdmin):
    list_display = ('sponsor_number', 'owner_client', 'group', 'is_active')
    search_fields = ('sponsor_number', 'name', 'owner_client__name_en')
    list_filter = ('is_active', 'group')