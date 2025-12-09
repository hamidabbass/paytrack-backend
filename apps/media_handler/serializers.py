"""
Media Handler Serializers - Serializers for file uploads
"""

from rest_framework import serializers
from django.conf import settings
from .models import MediaFile


class MediaFileSerializer(serializers.ModelSerializer):
    """Serializer for MediaFile model."""
    
    url = serializers.ReadOnlyField()
    
    class Meta:
        model = MediaFile
        fields = [
            'id', 'file', 'file_type', 'usage', 'original_name',
            'file_size', 'mime_type', 'duration', 'url', 'created_at'
        ]
        read_only_fields = ['id', 'uploaded_by', 'created_at']


class ImageUploadSerializer(serializers.Serializer):
    """Serializer for image upload."""
    
    image = serializers.ImageField(required=True)
    usage = serializers.ChoiceField(
        choices=MediaFile.USAGE_CHOICES,
        default='other'
    )
    
    def validate_image(self, value):
        # Check file size
        if value.size > settings.MAX_IMAGE_SIZE:
            max_mb = settings.MAX_IMAGE_SIZE / (1024 * 1024)
            raise serializers.ValidationError(
                f'Image size must be less than {max_mb}MB.'
            )
        
        # Check file type
        if value.content_type not in settings.ALLOWED_IMAGE_TYPES:
            raise serializers.ValidationError(
                f'Invalid image type. Allowed types: {", ".join(settings.ALLOWED_IMAGE_TYPES)}'
            )
        
        return value


class VoiceUploadSerializer(serializers.Serializer):
    """Serializer for voice note upload."""
    
    voice = serializers.FileField(required=True)
    duration = serializers.IntegerField(required=False, min_value=1)
    usage = serializers.ChoiceField(
        choices=MediaFile.USAGE_CHOICES,
        default='chat'
    )
    
    def validate_voice(self, value):
        # Check file size
        if value.size > settings.MAX_VOICE_SIZE:
            max_mb = settings.MAX_VOICE_SIZE / (1024 * 1024)
            raise serializers.ValidationError(
                f'Voice file size must be less than {max_mb}MB.'
            )
        
        # Check file type
        if value.content_type not in settings.ALLOWED_VOICE_TYPES:
            raise serializers.ValidationError(
                f'Invalid voice file type. Allowed types: {", ".join(settings.ALLOWED_VOICE_TYPES)}'
            )
        
        return value


class MultipleImageUploadSerializer(serializers.Serializer):
    """Serializer for multiple image upload."""
    
    images = serializers.ListField(
        child=serializers.ImageField(),
        max_length=5,
        required=True
    )
    usage = serializers.ChoiceField(
        choices=MediaFile.USAGE_CHOICES,
        default='other'
    )
    
    def validate_images(self, value):
        for image in value:
            if image.size > settings.MAX_IMAGE_SIZE:
                max_mb = settings.MAX_IMAGE_SIZE / (1024 * 1024)
                raise serializers.ValidationError(
                    f'Each image size must be less than {max_mb}MB.'
                )
            
            if image.content_type not in settings.ALLOWED_IMAGE_TYPES:
                raise serializers.ValidationError(
                    f'Invalid image type for {image.name}. Allowed types: {", ".join(settings.ALLOWED_IMAGE_TYPES)}'
                )
        
        return value
