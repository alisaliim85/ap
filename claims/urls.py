# D:\apps\ap\claims\urls.py

from django.urls import path
from . import views

app_name = 'claims'

urlpatterns = [
    # ==========================================
    # 1. العرض الأساسي (List & Detail)
    # ==========================================
    path('', views.claim_list, name='claim_list'),
    path('<uuid:pk>/', views.claim_detail, name='claim_detail'),
    
    path('create/', views.claim_create, name='claim_create'),
    path('create/search-member/', views.search_member_by_nid, name='search_member_by_nid'),
    
    path('<uuid:pk>/comment/', views.add_claim_comment, name='add_claim_comment'),

    # ==========================================
    # 2. إجراءات الإرسال والموارد البشرية (HR)
    # ==========================================
    path('<uuid:pk>/submit-to-hr/', views.submit_claim_to_hr, name='submit_to_hr'),
    path('<uuid:pk>/hr-approve/', views.hr_approve_claim, name='hr_approve_claim'),
    path('<uuid:pk>/hr-return/', views.hr_return_claim, name='hr_return_claim'),

    # ==========================================
    # 3. إجراءات الوسيط (Broker)
    # ==========================================
    path('<uuid:pk>/broker-start/', views.broker_start_processing, name='broker_start_processing'),
    path('<uuid:pk>/broker-return/', views.broker_return_claim, name='broker_return_claim'),
    path('<uuid:pk>/send-to-insurance/', views.send_to_insurance, name='send_to_insurance'),

    # ==========================================
    # 4. إجراءات شركة التأمين (Insurance)
    # ==========================================
    path('<uuid:pk>/insurance-query/', views.insurance_query_claim, name='insurance_query_claim'),
    path('<uuid:pk>/answer-insurance-query/', views.answer_insurance_query, name='answer_insurance_query'),
    path('<uuid:pk>/insurance-approve/', views.insurance_approve_claim, name='insurance_approve_claim'),
    path('<uuid:pk>/insurance-reject/', views.insurance_reject_claim, name='insurance_reject_claim'),

    # ==========================================
    # 5. الإجراء النهائي (السداد)
    # ==========================================
    path('<uuid:pk>/mark-as-paid/', views.mark_claim_as_paid, name='mark_claim_as_paid'),
]