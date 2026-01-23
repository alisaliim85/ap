from django.contrib import admin
from .models import BenefitType, Policy, PolicyClass, ClassBenefit

# تصحيح 1: يجب تعريف كلاس مخصص لـ BenefitType وإضافة search_fields
# لكي يعمل الـ autocomplete في ClassBenefitInline
@admin.register(BenefitType)
class BenefitTypeAdmin(admin.ModelAdmin):
    list_display = ('name_en', 'name_ar')
    search_fields = ('name_en', 'name_ar') 

class PolicyClassInline(admin.TabularInline):
    model = PolicyClass
    extra = 1

@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ('policy_number', 'client', 'provider', 'start_date', 'end_date', 'is_active')
    list_filter = ('provider', 'is_active')
    search_fields = ('policy_number', 'client__name_en')
    inlines = [PolicyClassInline]

class ClassBenefitInline(admin.TabularInline):
    model = ClassBenefit
    extra = 1
    autocomplete_fields = ['benefit_type']

@admin.register(PolicyClass)
class PolicyClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'policy', 'network', 'annual_limit')
    list_filter = ('policy__provider',)
    inlines = [ClassBenefitInline]
    
    # تصحيح 2: إضافة search_fields هنا لكي يعمل الـ autocomplete في MemberAdmin
    search_fields = ('name', 'policy__policy_number')