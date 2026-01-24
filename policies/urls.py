from django.urls import path
from . import views

app_name = 'policies'

urlpatterns = [
    path('', views.policy_list, name='policy_list'),
    path('add/', views.policy_create, name='policy_create'),
    path('<uuid:pk>/', views.policy_detail, name='policy_detail'),
    path('<uuid:pk>/edit/', views.policy_update, name='policy_update'),
    path('<uuid:pk>/delete/', views.policy_delete, name='policy_delete'),
    
    # الفئات والمنافع
    path('<uuid:policy_pk>/classes/add/', views.policy_class_create, name='policy_class_create'),
    path('classes/<uuid:class_pk>/benefits/', views.class_benefit_manage, name='class_benefit_manage'),
    
    # أنواع المنافع
    path('benefit-types/', views.benefit_type_list, name='benefit_type_list'),
]
