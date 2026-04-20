from django.contrib import admin
from .models import MedicationRequest, MedicationRefill, MedicationComment, MedicationStatusLog

@admin.register(MedicationRequest)
class MedicationRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'service_request', 'status', 'prescription_date', 'created_at')
    list_filter = ('status', 'interval_months')
    search_fields = ('service_request__id',)

@admin.register(MedicationRefill)
class MedicationRefillAdmin(admin.ModelAdmin):
    list_display = ('medication_request', 'cycle_number', 'scheduled_date', 'partner', 'status')
    list_filter = ('status', 'scheduled_date')

admin.site.register(MedicationComment)
admin.site.register(MedicationStatusLog)