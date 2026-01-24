from django.urls import path
from . import views

urlpatterns = [
    path('', views.partner_list, name='partner_list'),
    path('add/', views.partner_create, name='partner_create'),
    path('<uuid:pk>/', views.partner_detail, name='partner_detail'),
    path('<uuid:pk>/edit/', views.partner_update, name='partner_update'),
    path('<uuid:pk>/delete/', views.partner_delete, name='partner_delete'),
]
