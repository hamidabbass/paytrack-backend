"""
Core Views - Installment Plan and Payment endpoints
"""

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Sum, Count, Q
from django.utils import timezone

from apps.core.permissions import IsShopkeeper, IsBuyer, IsOwnerOrShopkeeper
from apps.core.models import InstallmentPlan, InstallmentPayment
from apps.core.serializers import (
    InstallmentPlanSerializer,
    InstallmentPlanListSerializer,
    InstallmentPlanCreateSerializer,
    InstallmentPaymentSerializer,
    InstallmentPaymentCreateSerializer,
    InstallmentPaymentVerifySerializer,
    BuyerInstallmentSummarySerializer,
)


class InstallmentPlanListView(generics.ListAPIView):
    """
    List all installment plans.
    GET /api/installments/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = InstallmentPlanListSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        if user.user_type == 'shopkeeper':
            queryset = InstallmentPlan.objects.filter(shopkeeper=user)
        else:
            queryset = InstallmentPlan.objects.filter(buyer=user)
        
        # Filter by status
        plan_status = self.request.query_params.get('status')
        if plan_status:
            queryset = queryset.filter(status=plan_status)
        
        # Filter by buyer (for shopkeeper)
        buyer_id = self.request.query_params.get('buyer_id')
        if buyer_id and user.user_type == 'shopkeeper':
            queryset = queryset.filter(buyer__id=buyer_id)
        
        return queryset.select_related('buyer', 'product').order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'success': True,
            'count': queryset.count(),
            'data': serializer.data
        })


class InstallmentPlanCreateView(generics.CreateAPIView):
    """
    Create a new installment plan.
    POST /api/installments/create/
    """
    permission_classes = [IsAuthenticated, IsShopkeeper]
    serializer_class = InstallmentPlanCreateSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = serializer.save()
        
        return Response({
            'success': True,
            'message': 'Installment plan created successfully.',
            'data': InstallmentPlanSerializer(plan).data
        }, status=status.HTTP_201_CREATED)


class InstallmentPlanDetailView(generics.RetrieveUpdateAPIView):
    """
    Get or update an installment plan.
    GET/PUT /api/installments/{id}/
    """
    permission_classes = [IsAuthenticated, IsOwnerOrShopkeeper]
    serializer_class = InstallmentPlanSerializer
    lookup_field = 'id'
    
    def get_queryset(self):
        user = self.request.user
        
        if user.user_type == 'shopkeeper':
            return InstallmentPlan.objects.filter(shopkeeper=user)
        else:
            return InstallmentPlan.objects.filter(buyer=user)
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        return Response({
            'success': True,
            'data': serializer.data
        })


class BuyerInstallmentsView(generics.ListAPIView):
    """
    Get all installments for a specific buyer.
    GET /api/installments/buyer/{buyer_id}/
    """
    permission_classes = [IsAuthenticated, IsShopkeeper]
    serializer_class = InstallmentPlanListSerializer
    
    def get_queryset(self):
        buyer_id = self.kwargs.get('buyer_id')
        return InstallmentPlan.objects.filter(
            shopkeeper=self.request.user,
            buyer__id=buyer_id
        ).order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        # Calculate summary
        summary = queryset.aggregate(
            total_amount=Sum('total_amount'),
            total_remaining=Sum('remaining_amount')
        )
        
        return Response({
            'success': True,
            'count': queryset.count(),
            'summary': {
                'total_amount': str(summary['total_amount'] or 0),
                'total_remaining': str(summary['total_remaining'] or 0)
            },
            'data': serializer.data
        })


class InstallmentPaymentSubmitView(APIView):
    """
    Submit payment proof for an installment.
    POST /api/installments/{plan_id}/payments/{payment_id}/submit/
    """
    permission_classes = [IsAuthenticated, IsBuyer]
    
    def post(self, request, plan_id, payment_id):
        try:
            payment = InstallmentPayment.objects.get(
                id=payment_id,
                installment_plan__id=plan_id,
                installment_plan__buyer=request.user
            )
        except InstallmentPayment.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Payment not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        if payment.status == 'verified':
            return Response({
                'success': False,
                'message': 'This payment has already been verified.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = InstallmentPaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Update payment with proof
        payment.payment_proof = serializer.validated_data['payment_proof']
        payment.payment_method = serializer.validated_data.get('payment_method', 'cash')
        payment.transaction_id = serializer.validated_data.get('transaction_id', '')
        payment.notes = serializer.validated_data.get('notes', '')
        payment.status = 'pending'
        payment.save()
        
        return Response({
            'success': True,
            'message': 'Payment proof submitted successfully.',
            'data': InstallmentPaymentSerializer(payment).data
        })


class InstallmentPaymentVerifyView(APIView):
    """
    Verify or reject a payment (Shopkeeper only).
    POST /api/installments/payments/{payment_id}/verify/
    """
    permission_classes = [IsAuthenticated, IsShopkeeper]
    
    def post(self, request, payment_id):
        try:
            payment = InstallmentPayment.objects.get(
                id=payment_id,
                installment_plan__shopkeeper=request.user
            )
        except InstallmentPayment.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Payment not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        if payment.status == 'verified':
            return Response({
                'success': False,
                'message': 'This payment has already been verified.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = InstallmentPaymentVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        action = serializer.validated_data['action']
        
        if action == 'verify':
            payment.verify_payment(request.user)
            message = 'Payment verified successfully.'
        else:
            payment.reject_payment(serializer.validated_data.get('rejection_reason', ''))
            message = 'Payment rejected.'
        
        return Response({
            'success': True,
            'message': message,
            'data': InstallmentPaymentSerializer(payment).data
        })


class PendingPaymentsView(generics.ListAPIView):
    """
    List all pending payments for verification.
    GET /api/installments/pending-payments/
    """
    permission_classes = [IsAuthenticated, IsShopkeeper]
    serializer_class = InstallmentPaymentSerializer
    
    def get_queryset(self):
        return InstallmentPayment.objects.filter(
            installment_plan__shopkeeper=self.request.user,
            status='pending',
            payment_proof__isnull=False
        ).select_related('installment_plan', 'installment_plan__buyer').order_by('due_date')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'success': True,
            'count': queryset.count(),
            'data': serializer.data
        })


class OverduePaymentsView(generics.ListAPIView):
    """
    List all overdue payments.
    GET /api/installments/overdue/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = InstallmentPaymentSerializer
    
    def get_queryset(self):
        user = self.request.user
        today = timezone.now().date()
        
        queryset = InstallmentPayment.objects.filter(
            status='pending',
            due_date__lt=today
        )
        
        if user.user_type == 'shopkeeper':
            queryset = queryset.filter(installment_plan__shopkeeper=user)
        else:
            queryset = queryset.filter(installment_plan__buyer=user)
        
        return queryset.order_by('due_date')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'success': True,
            'count': queryset.count(),
            'data': serializer.data
        })


class InstallmentStatsView(APIView):
    """
    Get installment statistics for dashboard.
    GET /api/installments/stats/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        today = timezone.now().date()
        
        if user.user_type == 'shopkeeper':
            plans = InstallmentPlan.objects.filter(shopkeeper=user)
            payments = InstallmentPayment.objects.filter(
                installment_plan__shopkeeper=user
            )
        else:
            plans = InstallmentPlan.objects.filter(buyer=user)
            payments = InstallmentPayment.objects.filter(
                installment_plan__buyer=user
            )
        
        stats = {
            'total_plans': plans.count(),
            'active_plans': plans.filter(status='active').count(),
            'completed_plans': plans.filter(status='completed').count(),
            'overdue_plans': plans.filter(status='overdue').count(),
            'total_amount': str(plans.aggregate(Sum('total_amount'))['total_amount__sum'] or 0),
            'total_collected': str(payments.filter(status='verified').aggregate(Sum('amount'))['amount__sum'] or 0),
            'total_pending': str(plans.filter(status__in=['active', 'overdue']).aggregate(Sum('remaining_amount'))['remaining_amount__sum'] or 0),
            'overdue_payments': payments.filter(status='pending', due_date__lt=today).count(),
            'pending_verification': payments.filter(status='pending', payment_proof__isnull=False).count() if user.user_type == 'shopkeeper' else 0,
        }
        
        return Response({
            'success': True,
            'data': stats
        })


class BuyerInstallmentSummaryView(APIView):
    """
    Get installment summary for the current buyer.
    GET /api/installments/my-summary/
    """
    permission_classes = [IsAuthenticated, IsBuyer]
    
    def get(self, request):
        user = request.user
        plans = InstallmentPlan.objects.filter(buyer=user)
        
        summary_data = plans.aggregate(
            total_plans=Count('id'),
            active_plans=Count('id', filter=Q(status='active')),
            completed_plans=Count('id', filter=Q(status='completed')),
            total_amount=Sum('total_amount'),
            total_remaining=Sum('remaining_amount', filter=Q(status__in=['active', 'overdue']))
        )
        
        # Get next payment
        next_payment = InstallmentPayment.objects.filter(
            installment_plan__buyer=user,
            status='pending'
        ).order_by('due_date').first()
        
        total_paid = InstallmentPayment.objects.filter(
            installment_plan__buyer=user,
            status='verified'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        summary = {
            'total_plans': summary_data['total_plans'] or 0,
            'active_plans': summary_data['active_plans'] or 0,
            'completed_plans': summary_data['completed_plans'] or 0,
            'total_amount': str(summary_data['total_amount'] or 0),
            'total_paid': str(total_paid),
            'total_pending': str(summary_data['total_remaining'] or 0),
            'next_payment_date': next_payment.due_date if next_payment else None,
            'next_payment_amount': str(next_payment.amount) if next_payment else None
        }
        
        return Response({
            'success': True,
            'data': summary
        })
