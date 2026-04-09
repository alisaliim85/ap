from django.contrib import admin
from .models import Broker, BrokerSubscription, BrokerPartnerContract

# إعداد عرض الاشتراكات كصفوف داخل صفحة الوسيط (Inline)
class BrokerSubscriptionInline(admin.TabularInline):
    model = BrokerSubscription
    extra = 1  # عدد الصفوف الفارغة للمدير لإضافة اشتراك جديد بسرعة
    fields = ('plan', 'start_date', 'end_date', 'is_active')

# إعداد عرض عقود الشركاء كصفوف داخل صفحة الوسيط (Inline)
class BrokerPartnerContractInline(admin.TabularInline):
    model = BrokerPartnerContract
    extra = 1
    autocomplete_fields = ['partner'] # لتسهيل البحث إذا كان عدد الشركاء كبيراً

@admin.register(Broker)
class BrokerAdmin(admin.ModelAdmin):
    list_display = ('name_ar', 'name_en', 'commercial_record', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name_ar', 'name_en', 'commercial_record')
    inlines = [BrokerSubscriptionInline, BrokerPartnerContractInline]

@admin.register(BrokerSubscription)
class BrokerSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('broker', 'plan', 'start_date', 'end_date', 'is_active')
    list_filter = ('plan', 'is_active', 'start_date')
    search_fields = ('broker__name_ar', 'broker__name_en')

@admin.register(BrokerPartnerContract)
class BrokerPartnerContractAdmin(admin.ModelAdmin):
    list_display = ('broker', 'partner', 'commission_rate', 'is_active')
    list_filter = ('is_active', 'broker')
    search_fields = ('broker__name_ar', 'partner__name_ar')
    autocomplete_fields = ['partner']