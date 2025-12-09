"""
Installment URL Configuration
"""

from django.urls import path
from apps.core.views.installment_views import (
    InstallmentPlanListView,
    InstallmentPlanCreateView,
    InstallmentPlanDetailView,
    BuyerInstallmentsView,
    InstallmentPaymentSubmitView,
    InstallmentPaymentVerifyView,
    PendingPaymentsView,
    OverduePaymentsView,
    InstallmentStatsView,
    BuyerInstallmentSummaryView,
)

urlpatterns = [
    path('', InstallmentPlanListView.as_view(), name='installment-list'),
    path('create/', InstallmentPlanCreateView.as_view(), name='installment-create'),
    path('stats/', InstallmentStatsView.as_view(), name='installment-stats'),
    path('my-summary/', BuyerInstallmentSummaryView.as_view(), name='buyer-summary'),
    path('pending-payments/', PendingPaymentsView.as_view(), name='pending-payments'),
    path('overdue/', OverduePaymentsView.as_view(), name='overdue-payments'),
    path('<uuid:id>/', InstallmentPlanDetailView.as_view(), name='installment-detail'),
    path('buyer/<uuid:buyer_id>/', BuyerInstallmentsView.as_view(), name='buyer-installments'),
    path('<uuid:plan_id>/payments/<uuid:payment_id>/submit/', InstallmentPaymentSubmitView.as_view(), name='payment-submit'),
    path('payments/<uuid:payment_id>/verify/', InstallmentPaymentVerifyView.as_view(), name='payment-verify'),
]
