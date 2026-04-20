from django.contrib import admin
from .models import (
    MedicationRequest, MedicationRefill, MedicationAttachment,
    MedicationComment, MedicationStatusLog,
)


class MedicationAttachmentInline(admin.TabularInline):
    model = MedicationAttachment
    extra = 0
    readonly_fields = ('original_attachment', 'uploaded_at')


class MedicationRefillInline(admin.TabularInline):
    model = MedicationRefill
    extra = 0
    readonly_fields = ('cycle_number', 'scheduled_date', 'partner', 'status', 'scheduled_by', 'approved_by', 'approved_at')
    can_delete = False
    show_change_link = True


class MedicationStatusLogInline(admin.TabularInline):
    model = MedicationStatusLog
    extra = 0
    readonly_fields = ('from_status', 'to_status', 'action', 'reason', 'user', 'created_at')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class RefillStatusLogInline(admin.TabularInline):
    model = MedicationStatusLog
    fk_name = 'refill'
    extra = 0
    readonly_fields = ('from_status', 'to_status', 'action', 'reason', 'user', 'created_at')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(MedicationRequest)
class MedicationRequestAdmin(admin.ModelAdmin):
    list_display = ('reference', 'service_request', 'status', 'prescription_date', 'created_by', 'created_at')
    list_filter = ('status', 'interval_months', 'prescription_date')
    search_fields = ('reference', 'service_request__reference')
    readonly_fields = ('reference', 'created_at', 'updated_at', 'created_by')
    inlines = [MedicationAttachmentInline, MedicationRefillInline, MedicationStatusLogInline]
    date_hierarchy = 'created_at'


@admin.register(MedicationRefill)
class MedicationRefillAdmin(admin.ModelAdmin):
    list_display = ('medication_request', 'cycle_number', 'scheduled_date', 'partner', 'status', 'scheduled_by')
    list_filter = ('status', 'scheduled_date')
    search_fields = ('medication_request__reference', 'partner__name_ar')
    readonly_fields = ('scheduled_by', 'approved_by', 'approved_at', 'actual_dispense_date')
    inlines = [RefillStatusLogInline]


@admin.register(MedicationComment)
class MedicationCommentAdmin(admin.ModelAdmin):
    list_display = ('medication_request', 'author', 'visibility', 'created_at')
    list_filter = ('visibility',)
    readonly_fields = ('created_at',)


@admin.register(MedicationStatusLog)
class MedicationStatusLogAdmin(admin.ModelAdmin):
    list_display = ('medication_request', 'refill', 'from_status', 'to_status', 'action', 'user', 'created_at')
    readonly_fields = ('from_status', 'to_status', 'action', 'reason', 'user', 'created_at')
