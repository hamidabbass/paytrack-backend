"""
URLs for customers app
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet, InstallmentRecordViewSet, PaymentRecordViewSet

router = DefaultRouter()
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'installments', InstallmentRecordViewSet, basename='installment-record')
router.register(r'payments', PaymentRecordViewSet, basename='payment-record')

urlpatterns = [
    path('', include(router.urls)),
]
