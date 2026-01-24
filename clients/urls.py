from django.urls import path
from . import views

urlpatterns = [
    path('', views.client_list, name='client_list'),
    path('add/', views.client_create, name='client_create'),
    path('<uuid:pk>/', views.client_detail, name='client_detail'),
    path('<uuid:pk>/edit/', views.client_update, name='client_update'),
    path('<uuid:pk>/delete/', views.client_delete, name='client_delete'),
]