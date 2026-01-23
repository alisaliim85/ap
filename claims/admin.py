from django.contrib import admin
from .models import Currency, Claim, ClaimAttachment, ClaimComment

admin.site.register(Currency)

class ClaimAttachmentInline(admin.TabularInline):
    model = ClaimAttachment
    extra = 0

class ClaimCommentInline(admin.TabularInline):
    model = ClaimComment
    extra = 0
    readonly_fields = ('created_at',)

@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ('claim_reference', 'member', 'service_date', 'amount_original', 'status', 'created_at')
    list_filter = ('status', 'is_international', 'is_in_patient')
    search_fields = ('claim_reference', 'member__full_name', 'member__medical_card_number')
    inlines = [ClaimAttachmentInline, ClaimCommentInline]
    autocomplete_fields = ['member']