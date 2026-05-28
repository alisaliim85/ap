from django.urls import path
from . import views

app_name = 'policies'

urlpatterns = [
    path('', views.policy_list, name='policy_list'),
    path('add/', views.policy_create, name='policy_create'),
    path('<uuid:pk>/', views.policy_detail, name='policy_detail'),
    path('<uuid:pk>/edit/', views.policy_update, name='policy_update'),
    path('<uuid:pk>/delete/', views.policy_delete, name='policy_delete'),

    # الفئات والمنافع (وثائق)
    path('<uuid:policy_pk>/classes/add/', views.policy_class_create, name='policy_class_create'),
    path('classes/<uuid:class_pk>/benefits/', views.class_benefit_manage, name='class_benefit_manage'),

    # أنواع المنافع
    path('benefit-types/', views.benefit_type_list, name='benefit_type_list'),

    # خطط التأمين (Insurance Plan Templates)
    path('plans/', views.plan_list, name='plan_list'),
    path('plans/create/', views.plan_create, name='plan_create'),
    path('plans/<uuid:plan_pk>/', views.plan_detail, name='plan_detail'),
    path('plans/<uuid:plan_pk>/edit/', views.plan_update, name='plan_update'),
    path('plans/<uuid:plan_pk>/classes/add/', views.plan_class_create, name='plan_class_create'),
    path('plans/<uuid:plan_pk>/classes/<uuid:class_pk>/benefits/', views.plan_class_benefit_manage, name='plan_class_benefit_manage'),
    # HTMX endpoint: خيارات الفئات لخطة معينة
    path('plans/<uuid:plan_pk>/get-classes/', views.plan_get_classes, name='plan_get_classes'),
]
