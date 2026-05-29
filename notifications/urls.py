# notifications/urls.py
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # HTMX partial: bell badge polling
    path('unread-count/', views.unread_count, name='unread-count'),
    # Mark actions
    path('mark-read/<uuid:pk>/', views.mark_read, name='mark-read'),
    path('mark-all-read/', views.mark_all_read, name='mark-all-read'),
]
