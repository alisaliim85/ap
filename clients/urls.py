from django.urls import path
from . import views

urlpatterns = [
    path('', views.client_list, name='client_list'),
    path('add/', views.client_create, name='client_create'),
    path('<uuid:pk>/', views.client_detail, name='client_detail'),
    path('<uuid:pk>/edit/', views.client_update, name='client_update'),
    path('<uuid:pk>/delete/', views.client_delete, name='client_delete'),
    # أرقام الكفيلة
    path('<uuid:pk>/sponsors/add/', views.sponsor_number_create, name='sponsor_number_create'),
    path('<uuid:pk>/sponsors/<uuid:sponsor_pk>/edit/', views.sponsor_number_update, name='sponsor_number_update'),
    path('<uuid:pk>/sponsors/<uuid:sponsor_pk>/toggle/', views.sponsor_number_toggle, name='sponsor_number_toggle'),
]