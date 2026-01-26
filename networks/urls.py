from django.urls import path
from . import views

app_name = 'networks'

urlpatterns = [
    # مقدمي الخدمة
    path('service-providers/', views.service_provider_list, name='service_provider_list'),
    path('service-providers/add/', views.service_provider_create, name='service_provider_create'),
    path('service-providers/<uuid:pk>/edit/', views.service_provider_update, name='service_provider_update'),
    path('service-providers/<uuid:pk>/delete/', views.service_provider_delete, name='service_provider_delete'),
    
    # الشبكات الطبية
    path('', views.network_list, name='network_list'),
    path('add/', views.network_create, name='network_create'),
    path('<uuid:pk>/edit/', views.network_update, name='network_update'),
    path('<uuid:pk>/delete/', views.network_delete, name='network_delete'),
    path('<uuid:pk>/manage-hospitals/', views.network_manage_hospitals, name='network_manage_hospitals'),
]
