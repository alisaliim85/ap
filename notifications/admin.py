# notifications/admin.py
from django.contrib import admin
from .models import Notification, Message


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    # raw_id_fields works on FK fields (recipient, content_type) — NOT on UUIDField (object_id)
    raw_id_fields = ('recipient', 'content_type')
    readonly_fields = ('content_object',)   # GenericFK — display only, no dropdown
    list_per_page = 25
    list_select_related = True
    list_display = ('recipient', 'notification_type', 'title', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('recipient__username', 'recipient__first_name', 'title')
    date_hierarchy = 'created_at'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    raw_id_fields = ('sender', 'recipient', 'parent', 'content_type')
    readonly_fields = ('content_object',)
    list_per_page = 25
    list_select_related = ('sender', 'recipient')
    list_display = ('sender', 'recipient', 'subject', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('sender__username', 'recipient__username', 'subject')
    date_hierarchy = 'created_at'
