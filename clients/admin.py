from django.contrib import admin
from .models import Client

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name_en', 'name_ar', 'parent', 'commercial_record', 'is_active')
    search_fields = ('name_en', 'name_ar', 'commercial_record')
    list_filter = ('is_active',)
    # يسمح بالبحث عن هذا المودل في مودلز أخرى
    search_fields = ['name_en', 'commercial_record']