"""
Admin registration for Media Handler app
"""

from django.contrib import admin
from .models import MediaFile


@admin.register(MediaFile)
class MediaFileAdmin(admin.ModelAdmin):
    list_display = ['id', 'uploaded_by', 'file_type', 'usage', 'original_name', 'file_size', 'created_at']
    list_filter = ['file_type', 'usage', 'created_at']
    search_fields = ['uploaded_by__email', 'original_name']
    raw_id_fields = ['uploaded_by']
    readonly_fields = ['created_at']
