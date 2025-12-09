"""
Dashboard URL Configuration
"""

from django.urls import path
from apps.core.views.dashboard_views import ShopkeeperDashboardView

urlpatterns = [
    path('', ShopkeeperDashboardView.as_view(), name='shopkeeper-dashboard'),
]
