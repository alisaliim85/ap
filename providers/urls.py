from django.urls import path
from . import views

urlpatterns = [
    path('', views.provider_list, name='provider_list'),
    path('add/', views.provider_create, name='provider_create'),
    path('<uuid:pk>/', views.provider_detail, name='provider_detail'),
    path('<uuid:pk>/edit/', views.provider_update, name='provider_update'),
    path('<uuid:pk>/delete/', views.provider_delete, name='provider_delete'),
]
