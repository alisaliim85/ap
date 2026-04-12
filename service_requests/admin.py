from django.contrib import admin
from .models import RequestType, ServiceRequest, RequestAttachment, RequestStatusLog


@admin.register(RequestType)
class RequestTypeAdmin(admin.ModelAdmin):
    list_display = ('name_ar', 'name_en', 'icon', 'is_active', 'display_order')
    list_editable = ('is_active', 'display_order')
    list_filter = ('is_active',)
    search_fields = ('name_ar', 'name_en')


class RequestAttachmentInline(admin.TabularInline):
    model = RequestAttachment
    extra = 0
    readonly_fields = ('uploaded_at',)


class RequestStatusLogInline(admin.TabularInline):
    model = RequestStatusLog
    extra = 0
    readonly_fields = ('from_status', 'to_status', 'action', 'note', 'user', 'created_at')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ('reference', 'request_type', 'member', 'status', 'submitted_by', 'created_at')
    list_filter = ('status', 'request_type', 'submitted_on_behalf')
    search_fields = ('reference', 'member__full_name', 'member__national_id')
    readonly_fields = ('id', 'reference', 'created_at', 'updated_at', 'submitted_at')
    inlines = [RequestAttachmentInline, RequestStatusLogInline]
