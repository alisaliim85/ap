from django.urls import path
from . import views, views_upload

app_name = 'members'

urlpatterns = [
    path('', views.member_list, name='member_list'),
    path('add/', views.member_create, name='member_create'),
    path('<uuid:pk>/', views.member_detail, name='member_detail'),
    path('<uuid:pk>/edit/', views.member_update, name='member_update'),
    path('<uuid:pk>/delete/', views.member_delete, name='member_delete'),
    
    # Upload / Template
    path('upload/', views_upload.MemberBulkUploadView.as_view(), name='member_bulk_upload'),
    path('upload/template/', views_upload.MemberDownloadTemplateView.as_view(), name='member_download_template'),

    # AJAX / HTMX
    path('ajax/load-policy-classes/', views.load_policy_classes, name='ajax_load_policy_classes'),

    # Member Portal
    path('dashboard/', views.my_dashboard, name='member_dashboard'),
    path('my-family/', views.my_family_members, name='my_family_members'),
]
