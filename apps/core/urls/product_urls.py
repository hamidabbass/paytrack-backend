"""
Product URL Configuration
"""

from django.urls import path
from apps.core.views.product_views import (
    ProductListView,
    ProductDetailView,
    ProductCategoriesView,
)

urlpatterns = [
    path('', ProductListView.as_view(), name='product-list'),
    path('categories/', ProductCategoriesView.as_view(), name='product-categories'),
    path('<uuid:id>/', ProductDetailView.as_view(), name='product-detail'),
]
