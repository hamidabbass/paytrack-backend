"""
Buyer URL Configuration
"""

from django.urls import path
from apps.core.views.buyer_views import (
    BuyerListCreateView,
    BuyerDetailView,
    BuyerSearchView,
    BuyerStatsView,
    BuyerBlacklistView,
)

urlpatterns = [
    path('', BuyerListCreateView.as_view(), name='buyer-list'),
    path('search/', BuyerSearchView.as_view(), name='buyer-search'),
    path('stats/', BuyerStatsView.as_view(), name='buyer-stats'),
    path('<uuid:id>/', BuyerDetailView.as_view(), name='buyer-detail'),
    path('<uuid:id>/blacklist/', BuyerBlacklistView.as_view(), name='buyer-blacklist'),
]
