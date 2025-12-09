"""
Main URL Configuration for installment_app project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API Endpoints
    path('api/auth/', include('apps.users.urls')),
    path('api/', include('apps.customers.urls')),  # Customer management
    path('api/products/', include('apps.core.urls.product_urls')),
    path('api/core/dashboard/', include('apps.core.urls.dashboard_urls')),
    path('api/upload/', include('apps.media_handler.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
