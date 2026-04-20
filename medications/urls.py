from django.urls import path
from . import views

app_name = 'medications'

urlpatterns = [
    # مسارات الوسيط
    path('broker/list/', views.broker_medication_list, name='broker_medication_list'),
    path('broker/<uuid:request_id>/schedule/', views.schedule_medication, name='schedule_medication'),
    
    # مسار تحديث الحالة (للصيدلية/الوسيط)
    path('refill/<uuid:refill_id>/status/', views.change_refill_status, name='change_refill_status'),
]