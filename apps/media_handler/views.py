"""
Media Handler Views - File upload endpoints
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import uuid
import os

from .models import MediaFile
from .serializers import (
    MediaFileSerializer,
    ImageUploadSerializer,
    VoiceUploadSerializer,
    MultipleImageUploadSerializer,
)


class ImageUploadView(APIView):
    """
    Upload a single image.
    POST /api/upload/image/
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        serializer = ImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        image = serializer.validated_data['image']
        usage = serializer.validated_data.get('usage', 'other')
        
        # Generate unique filename
        ext = os.path.splitext(image.name)[1]
        filename = f"{uuid.uuid4()}{ext}"
        path = f"images/{usage}/{filename}"
        
        # Save file
        saved_path = default_storage.save(path, ContentFile(image.read()))
        file_url = default_storage.url(saved_path)
        
        # Create media file record
        media_file = MediaFile.objects.create(
            uploaded_by=request.user,
            file=saved_path,
            file_type='image',
            usage=usage,
            original_name=image.name,
            file_size=image.size,
            mime_type=image.content_type
        )
        
        return Response({
            'success': True,
            'message': 'Image uploaded successfully.',
            'data': {
                'id': str(media_file.id),
                'url': file_url,
                'original_name': image.name,
                'file_size': image.size
            }
        }, status=status.HTTP_201_CREATED)


class VoiceUploadView(APIView):
    """
    Upload a voice note.
    POST /api/upload/voice/
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        serializer = VoiceUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        voice = serializer.validated_data['voice']
        duration = serializer.validated_data.get('duration')
        usage = serializer.validated_data.get('usage', 'chat')
        
        # Generate unique filename
        ext = os.path.splitext(voice.name)[1] or '.m4a'
        filename = f"{uuid.uuid4()}{ext}"
        path = f"voice/{filename}"
        
        # Save file
        saved_path = default_storage.save(path, ContentFile(voice.read()))
        file_url = default_storage.url(saved_path)
        
        # Create media file record
        media_file = MediaFile.objects.create(
            uploaded_by=request.user,
            file=saved_path,
            file_type='voice',
            usage=usage,
            original_name=voice.name,
            file_size=voice.size,
            mime_type=voice.content_type,
            duration=duration
        )
        
        return Response({
            'success': True,
            'message': 'Voice note uploaded successfully.',
            'data': {
                'id': str(media_file.id),
                'url': file_url,
                'original_name': voice.name,
                'file_size': voice.size,
                'duration': duration
            }
        }, status=status.HTTP_201_CREATED)


class MultipleImageUploadView(APIView):
    """
    Upload multiple images at once.
    POST /api/upload/images/
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        serializer = MultipleImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        images = serializer.validated_data['images']
        usage = serializer.validated_data.get('usage', 'other')
        
        uploaded_files = []
        
        for image in images:
            # Generate unique filename
            ext = os.path.splitext(image.name)[1]
            filename = f"{uuid.uuid4()}{ext}"
            path = f"images/{usage}/{filename}"
            
            # Save file
            saved_path = default_storage.save(path, ContentFile(image.read()))
            file_url = default_storage.url(saved_path)
            
            # Create media file record
            media_file = MediaFile.objects.create(
                uploaded_by=request.user,
                file=saved_path,
                file_type='image',
                usage=usage,
                original_name=image.name,
                file_size=image.size,
                mime_type=image.content_type
            )
            
            uploaded_files.append({
                'id': str(media_file.id),
                'url': file_url,
                'original_name': image.name,
                'file_size': image.size
            })
        
        return Response({
            'success': True,
            'message': f'{len(uploaded_files)} images uploaded successfully.',
            'data': uploaded_files
        }, status=status.HTTP_201_CREATED)


class MediaListView(APIView):
    """
    List all media files uploaded by the user.
    GET /api/upload/list/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        file_type = request.query_params.get('type')
        usage = request.query_params.get('usage')
        
        queryset = MediaFile.objects.filter(uploaded_by=request.user)
        
        if file_type:
            queryset = queryset.filter(file_type=file_type)
        if usage:
            queryset = queryset.filter(usage=usage)
        
        queryset = queryset.order_by('-created_at')[:50]
        
        serializer = MediaFileSerializer(queryset, many=True)
        
        return Response({
            'success': True,
            'count': queryset.count(),
            'data': serializer.data
        })


class MediaDeleteView(APIView):
    """
    Delete a media file.
    DELETE /api/upload/{id}/
    """
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, id):
        try:
            media_file = MediaFile.objects.get(
                id=id,
                uploaded_by=request.user
            )
        except MediaFile.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Media file not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Delete file from storage
        if media_file.file:
            default_storage.delete(media_file.file.name)
        
        media_file.delete()
        
        return Response({
            'success': True,
            'message': 'Media file deleted successfully.'
        })
