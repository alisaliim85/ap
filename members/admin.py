from django.contrib import admin
from .models import Member, MemberDocument

class MemberDocumentInline(admin.TabularInline):
    model = MemberDocument
    extra = 0

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'medical_card_number', 'client', 'relation', 'sponsor', 'is_active')
    list_filter = ('client', 'relation', 'gender')
    search_fields = ('full_name', 'medical_card_number', 'national_id')
    inlines = [MemberDocumentInline]
    
    # هام جداً: يجعل حقول ForeignKey قابلة للبحث بدلاً من القائمة المنسدلة
    autocomplete_fields = ['client', 'sponsor', 'policy_class']