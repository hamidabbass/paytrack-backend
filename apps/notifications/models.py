"""
Notification Models
Handles in-app notifications for users
"""

from django.db import models
from django.conf import settings
import uuid


class Notification(models.Model):
    """
    Notification model for storing user notifications.
    """
    
    NOTIFICATION_TYPES = (
        ('payment_due', 'Payment Due'),
        ('payment_received', 'Payment Received'),
        ('payment_overdue', 'Payment Overdue'),
        ('new_buyer', 'New Buyer'),
        ('new_product', 'New Product'),
        ('plan_created', 'Plan Created'),
        ('plan_completed', 'Plan Completed'),
        ('message', 'New Message'),
        ('reminder', 'Reminder'),
        ('system', 'System'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    # Notification content
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, default='system')
    
    # Optional reference to related object
    reference_id = models.UUIDField(null=True, blank=True)
    reference_type = models.CharField(max_length=50, null=True, blank=True)  # 'buyer', 'product', 'plan', 'payment'
    
    # Additional data as JSON
    data = models.JSONField(default=dict, blank=True)
    
    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.email}"
    
    def mark_as_read(self):
        from django.utils import timezone
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=['is_read', 'read_at'])
