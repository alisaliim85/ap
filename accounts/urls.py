from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # إدارة المستخدمين
    path('users/', views.user_list, name='user_list'),
    path('users/add/', views.user_create, name='user_create'),
    path('users/<uuid:pk>/edit/', views.user_update, name='user_update'),
    path('users/<uuid:pk>/delete/', views.user_delete, name='user_delete'),

    # إدارة موظفي الـ HR
    path('staff/', views.hr_user_list, name='hr_user_list'),
    path('staff/add/', views.hr_user_create, name='hr_user_create'),
    path('staff/<uuid:pk>/edit/', views.hr_user_update, name='hr_user_update'),
    path('staff/<uuid:pk>/delete/', views.hr_user_delete, name='hr_user_delete'),

    # الملف الشخصي
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.user_profile_edit, name='profile_edit'),
]
