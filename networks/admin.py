from django.contrib import admin
from .models import ServiceProvider, Network

@admin.register(ServiceProvider)
class ServiceProviderAdmin(admin.ModelAdmin):
    # تصحيح: إزالة 'phone_number' لأننا لم نضفه في المودل
    list_display = ('name_en', 'type', 'city') 
    list_filter = ('type', 'city')
    search_fields = ('name_en', 'name_ar')

@admin.register(Network)
class NetworkAdmin(admin.ModelAdmin):
    list_display = ('name_en', 'provider', 'hospital_count')
    list_filter = ('provider',)
    filter_horizontal = ('hospitals',)

    def hospital_count(self, obj):
        return obj.hospitals.count()
    hospital_count.short_description = "Hospitals Count"