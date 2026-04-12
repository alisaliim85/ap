from django.urls import path
from . import views

app_name = 'service_requests'

urlpatterns = [
    # ==========================================
    # 1. العرض الأساسي (List & Detail)
    # ==========================================
    path('', views.request_list, name='request_list'),
    path('create/', views.request_create, name='request_create'),
    path('<uuid:pk>/', views.request_detail, name='request_detail'),
    path('<uuid:pk>/edit/', views.request_edit, name='request_edit'),
    path('<uuid:pk>/delete/', views.request_delete, name='request_delete'),
    path('<uuid:pk>/add-attachment/', views.add_attachment, name='add_attachment'),

    # ==========================================
    # 2. HTMX Partials
    # ==========================================
    path('get-fields/<int:type_id>/', views.request_type_fields, name='request_type_fields'),
    path('search-member/', views.search_member_by_nid, name='search_member'),

    # ==========================================
    # 3. إرسال الطلب (Member / HR)
    # ==========================================
    path('<uuid:pk>/submit/', views.submit_request, name='submit_request'),

    # ==========================================
    # 3. إجراءات الوسيط (Broker Actions)
    # ==========================================
    path('<uuid:pk>/start-review/', views.broker_start_review, name='broker_start_review'),
    path('<uuid:pk>/return/', views.broker_return_request, name='broker_return_request'),
    path('<uuid:pk>/resolve/', views.broker_resolve_request, name='broker_resolve_request'),
    path('<uuid:pk>/reject/', views.broker_reject_request, name='broker_reject_request'),
]
