from django.contrib import admin
from .models import (
    ChronicDisease, ChronicRequest, ChronicCase, 
    HomeVisit, VisitPrescription, VisitLabRequest
)

admin.site.register(ChronicDisease)

@admin.register(ChronicRequest)
class ChronicRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'member', 'disease', 'status', 'created_at')
    list_filter = ('status', 'disease')
    search_fields = ('member__full_name',)
    autocomplete_fields = ['member', 'assigned_partner']

# --- إعدادات ملف الحالة ---
class HomeVisitInline(admin.TabularInline):
    model = HomeVisit
    fields = ('scheduled_date', 'doctor', 'status')
    readonly_fields = ('scheduled_date',)
    extra = 0
    show_change_link = True 

@admin.register(ChronicCase)
class ChronicCaseAdmin(admin.ModelAdmin):
    list_display = ('request_member_name', 'managing_partner', 'next_visit_due', 'status')
    list_filter = ('status', 'frequency_days')
    inlines = [HomeVisitInline]

    def request_member_name(self, obj):
        return obj.request.member.full_name
    request_member_name.short_description = "Patient"

# --- إعدادات الزيارات ---
class VisitPrescriptionInline(admin.TabularInline):
    model = VisitPrescription
    extra = 1

class VisitLabRequestInline(admin.TabularInline):
    model = VisitLabRequest
    extra = 1

@admin.register(HomeVisit)
class HomeVisitAdmin(admin.ModelAdmin):
    list_display = ('case_patient', 'scheduled_date', 'doctor', 'status')
    list_filter = ('status', 'scheduled_date')
    inlines = [VisitPrescriptionInline, VisitLabRequestInline]

    def case_patient(self, obj):
        return obj.case.request.member.full_name
    case_patient.short_description = "Patient"