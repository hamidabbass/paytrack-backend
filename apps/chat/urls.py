"""
Chat URL Configuration
"""

from django.urls import path
from .views import (
    ConversationListView,
    ConversationCreateView,
    ConversationDetailView,
    MessageListView,
    MessageSendView,
    MessageMarkReadView,
    UnreadCountView,
)

urlpatterns = [
    path('conversations/', ConversationListView.as_view(), name='conversation-list'),
    path('create/', ConversationCreateView.as_view(), name='conversation-create'),
    path('conversations/<uuid:id>/', ConversationDetailView.as_view(), name='conversation-detail'),
    path('messages/<uuid:conversation_id>/', MessageListView.as_view(), name='message-list'),
    path('send/<uuid:conversation_id>/', MessageSendView.as_view(), name='message-send'),
    path('messages/read/<uuid:conversation_id>/', MessageMarkReadView.as_view(), name='message-read'),
    path('unread-count/', UnreadCountView.as_view(), name='unread-count'),
]
