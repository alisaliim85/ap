from django.urls import path
from . import views

app_name = 'medications'

urlpatterns = [
    # لوحة التحكم الرئيسية
    path('dashboard/', views.medication_dashboard, name='medication_dashboard'),

    # نقل طلب الخدمة إلى وحدة الأدوية
    path('transfer/<uuid:service_request_id>/', views.transfer_to_medications, name='transfer_to_medications'),

    # جدولة دورة صرف
    path('<uuid:medication_request_id>/schedule/', views.schedule_refill, name='schedule_refill'),

    # مراجعة وقبول/رفض دورة الصرف
    path('refill/<uuid:refill_id>/review/', views.review_refill, name='review_refill'),

    # تفاصيل طلب دواء
    path('<uuid:medication_request_id>/detail/', views.medication_detail, name='medication_detail'),

    # تغيير حالة طلب الأدوية (تفعيل / إكمال / إلغاء)
    path('<uuid:medication_request_id>/status/', views.change_medication_status, name='change_medication_status'),

    # الصيدلية: قائمة الدورات المعتمدة
    path('pharmacy/', views.pharmacy_refill_list, name='pharmacy_refill_list'),
    path('pharmacy/refill/<uuid:refill_id>/', views.pharmacy_refill_detail, name='pharmacy_refill_detail'),
    path('pharmacy/refill/<uuid:refill_id>/status/', views.update_refill_status, name='update_refill_status'),
]
