"""
Notification URLs
"""

from django.urls import path
from .views import (
    NotificationListView,
    NotificationDetailView,
    MarkNotificationsReadView,
    UnreadCountView,
    ClearAllNotificationsView,
    GeneratePaymentRemindersView,
    GetPaymentRemindersView,
)

urlpatterns = [
    path('', NotificationListView.as_view(), name='notification-list'),
    path('<uuid:id>/', NotificationDetailView.as_view(), name='notification-detail'),
    path('mark-read/', MarkNotificationsReadView.as_view(), name='mark-notifications-read'),
    path('unread-count/', UnreadCountView.as_view(), name='unread-count'),
    path('clear-all/', ClearAllNotificationsView.as_view(), name='clear-all-notifications'),
    path('payment-reminders/', GetPaymentRemindersView.as_view(), name='payment-reminders'),
    path('generate-reminders/', GeneratePaymentRemindersView.as_view(), name='generate-reminders'),
]
