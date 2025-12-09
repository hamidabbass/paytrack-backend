"""
Chat Models - Conversation and Message models
"""

from django.db import models
from django.conf import settings
import uuid


class Conversation(models.Model):
    """
    Conversation model representing a chat between shopkeeper and buyer.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shopkeeper = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shopkeeper_conversations',
        limit_choices_to={'user_type': 'shopkeeper'}
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='buyer_conversations',
        limit_choices_to={'user_type': 'buyer'}
    )
    
    # Last message preview for listing
    last_message = models.TextField(blank=True, null=True)
    last_message_at = models.DateTimeField(blank=True, null=True)
    last_message_sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )
    
    # Unread counts
    shopkeeper_unread_count = models.IntegerField(default=0)
    buyer_unread_count = models.IntegerField(default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'conversations'
        verbose_name = 'Conversation'
        verbose_name_plural = 'Conversations'
        ordering = ['-last_message_at', '-created_at']
        unique_together = ['shopkeeper', 'buyer']
        indexes = [
            models.Index(fields=['shopkeeper']),
            models.Index(fields=['buyer']),
            models.Index(fields=['last_message_at']),
        ]
    
    def __str__(self):
        return f"Chat: {self.shopkeeper.full_name} <-> {self.buyer.full_name}"
    
    def mark_as_read(self, user):
        """Mark all messages as read for a user."""
        if user == self.shopkeeper:
            self.shopkeeper_unread_count = 0
        elif user == self.buyer:
            self.buyer_unread_count = 0
        self.save()
        
        # Mark individual messages as read
        Message.objects.filter(
            conversation=self,
            receiver=user,
            is_read=False
        ).update(is_read=True)
    
    def get_unread_count(self, user):
        """Get unread message count for a user."""
        if user == self.shopkeeper:
            return self.shopkeeper_unread_count
        elif user == self.buyer:
            return self.buyer_unread_count
        return 0


class Message(models.Model):
    """
    Message model for individual messages in a conversation.
    Supports text, images, and voice notes.
    """
    
    MESSAGE_TYPE_CHOICES = (
        ('text', 'Text'),
        ('image', 'Image'),
        ('voice', 'Voice Note'),
        ('document', 'Document'),
        ('system', 'System Message'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_messages'
    )
    
    # Message Content
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default='text')
    message_text = models.TextField(blank=True, null=True)
    
    # Media Attachments
    image = models.ImageField(upload_to='chat/images/', blank=True, null=True)
    voice_note = models.FileField(upload_to='chat/voice/', blank=True, null=True)
    voice_duration = models.IntegerField(blank=True, null=True)  # Duration in seconds
    document = models.FileField(upload_to='chat/documents/', blank=True, null=True)
    document_name = models.CharField(max_length=255, blank=True, null=True)
    
    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'messages'
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation']),
            models.Index(fields=['sender']),
            models.Index(fields=['receiver']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_read']),
        ]
    
    def __str__(self):
        return f"Message from {self.sender.full_name} - {self.message_type}"
    
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        
        if is_new:
            # Update conversation with last message info
            conversation = self.conversation
            conversation.last_message = self.get_preview_text()
            conversation.last_message_at = self.created_at
            conversation.last_message_sender = self.sender
            
            # Update unread count for receiver
            if self.receiver == conversation.shopkeeper:
                conversation.shopkeeper_unread_count += 1
            else:
                conversation.buyer_unread_count += 1
            
            conversation.save()
    
    def get_preview_text(self):
        """Get preview text for conversation listing."""
        if self.message_type == 'text':
            return self.message_text[:100] if self.message_text else ''
        elif self.message_type == 'image':
            return '📷 Image'
        elif self.message_type == 'voice':
            return '🎤 Voice message'
        elif self.message_type == 'document':
            return f'📄 {self.document_name or "Document"}'
        return ''
    
    def mark_as_read(self):
        """Mark message as read."""
        from django.utils import timezone
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()
