# notifications/urls.py
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # ── Notification views ──────────────────────────────────────────────────
    path('', views.NotificationListView.as_view(), name='list'),
    path('unread-count/', views.unread_count, name='unread-count'),
    path('mark-read/<uuid:pk>/', views.mark_read, name='mark-read'),
    path('mark-all-read/', views.mark_all_read, name='mark-all-read'),

    # ── Message views ───────────────────────────────────────────────────────
    path('messages/', views.MessageInboxView.as_view(), name='inbox'),
    path('messages/compose/', views.ComposeMessageView.as_view(), name='compose'),
    path('messages/<uuid:pk>/', views.MessageThreadView.as_view(), name='thread'),
    path('messages/<uuid:pk>/reply/', views.ReplyMessageView.as_view(), name='reply'),
]
