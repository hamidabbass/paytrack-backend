"""
Media Handler URL Configuration
"""

from django.urls import path
from .views import (
    ImageUploadView,
    VoiceUploadView,
    MultipleImageUploadView,
    MediaListView,
    MediaDeleteView,
)

urlpatterns = [
    path('image/', ImageUploadView.as_view(), name='upload-image'),
    path('voice/', VoiceUploadView.as_view(), name='upload-voice'),
    path('images/', MultipleImageUploadView.as_view(), name='upload-images'),
    path('list/', MediaListView.as_view(), name='media-list'),
    path('<uuid:id>/', MediaDeleteView.as_view(), name='media-delete'),
]
