"""
Media Models - MediaFile model for tracking uploads
"""

from django.db import models
from django.conf import settings
import uuid


class MediaFile(models.Model):
    """
    Generic model for tracking all media uploads.
    """
    
    FILE_TYPE_CHOICES = (
        ('image', 'Image'),
        ('voice', 'Voice Note'),
        ('document', 'Document'),
    )
    
    USAGE_CHOICES = (
        ('profile', 'Profile Image'),
        ('cnic', 'CNIC Document'),
        ('invoice', 'Invoice'),
        ('payment_proof', 'Payment Proof'),
        ('product', 'Product Image'),
        ('chat', 'Chat Attachment'),
        ('other', 'Other'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='uploaded_files'
    )
    
    # File Details
    file = models.FileField(upload_to='uploads/')
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES)
    usage = models.CharField(max_length=20, choices=USAGE_CHOICES, default='other')
    original_name = models.CharField(max_length=255)
    file_size = models.IntegerField()  # Size in bytes
    mime_type = models.CharField(max_length=100)
    
    # For voice files
    duration = models.IntegerField(blank=True, null=True)  # Duration in seconds
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'media_files'
        verbose_name = 'Media File'
        verbose_name_plural = 'Media Files'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['uploaded_by']),
            models.Index(fields=['file_type']),
            models.Index(fields=['usage']),
        ]
    
    def __str__(self):
        return f"{self.original_name} ({self.file_type})"
    
    @property
    def url(self):
        """Return the file URL."""
        return self.file.url if self.file else None
