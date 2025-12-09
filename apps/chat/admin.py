"""
Admin registration for Chat app
"""

from django.contrib import admin
from .models import Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'shopkeeper', 'buyer', 'last_message_at', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['shopkeeper__email', 'buyer__email']
    raw_id_fields = ['shopkeeper', 'buyer', 'last_message_sender']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'sender', 'message_type', 'is_read', 'created_at']
    list_filter = ['message_type', 'is_read', 'created_at']
    search_fields = ['sender__email', 'message_text']
    raw_id_fields = ['conversation', 'sender', 'receiver']
    readonly_fields = ['created_at', 'updated_at']
