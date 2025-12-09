"""
Views for Customer, InstallmentRecord, and PaymentRecord
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Q

from .models import Customer, InstallmentRecord, PaymentRecord
from .serializers import (
    CustomerSerializer, CustomerListSerializer, CustomerCreateSerializer,
    InstallmentRecordSerializer, InstallmentRecordCreateSerializer,
    PaymentRecordSerializer, PaymentRecordCreateSerializer
)


class CustomerViewSet(viewsets.ModelViewSet):
    """ViewSet for Customer CRUD operations."""
    
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'father_name', 'mobile_number', 'address']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Customer.objects.filter(shopkeeper=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'list':
            return CustomerListSerializer
        elif self.action == 'create':
            return CustomerCreateSerializer
        return CustomerSerializer
    
    def perform_create(self, serializer):
        serializer.save(shopkeeper=self.request.user)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get customer statistics."""
        customers = self.get_queryset()
        
        total_customers = customers.count()
        active_customers = customers.filter(is_active=True).count()
        
        # Get total pending amount
        total_pending = InstallmentRecord.objects.filter(
            shopkeeper=request.user,
            is_completed=False
        ).aggregate(total=Sum('remaining_amount'))['total'] or 0
        
        # Get total collected
        total_collected = PaymentRecord.objects.filter(
            installment_record__shopkeeper=request.user
        ).aggregate(total=Sum('amount_paid'))['total'] or 0
        
        # Add advance payments
        advance_total = InstallmentRecord.objects.filter(
            shopkeeper=request.user
        ).aggregate(total=Sum('advance_payment'))['total'] or 0
        
        total_collected += advance_total
        
        return Response({
            'total_customers': total_customers,
            'active_customers': active_customers,
            'total_pending': str(total_pending),
            'total_collected': str(total_collected),
        })


class InstallmentRecordViewSet(viewsets.ModelViewSet):
    """ViewSet for InstallmentRecord CRUD operations."""
    
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['customer__name', 'product_name']
    ordering_fields = ['created_at', 'total_cost', 'remaining_amount']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = InstallmentRecord.objects.filter(shopkeeper=self.request.user)
        # Filter by customer if provided
        customer_id = self.request.query_params.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        # Filter by completion status if provided
        is_completed = self.request.query_params.get('is_completed')
        if is_completed is not None:
            queryset = queryset.filter(is_completed=is_completed.lower() == 'true')
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create':
            return InstallmentRecordCreateSerializer
        return InstallmentRecordSerializer
    
    def create(self, request, *args, **kwargs):
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Received installment data: {request.data}")
        
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def perform_create(self, serializer):
        serializer.save(shopkeeper=self.request.user)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get all active (incomplete) installment records."""
        queryset = self.get_queryset().filter(is_completed=False)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def completed(self, request):
        """Get all completed installment records."""
        queryset = self.get_queryset().filter(is_completed=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_payment(self, request, pk=None):
        """Add a payment to the installment record."""
        installment = self.get_object()
        
        if installment.is_completed:
            return Response(
                {'error': 'This installment is already completed.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = PaymentRecordCreateSerializer(data={
            'installment_record': str(installment.id),
            'amount_paid': request.data.get('amount_paid'),
            'payment_date': request.data.get('payment_date'),
            'notes': request.data.get('notes', '')
        })
        
        if serializer.is_valid():
            serializer.save()
            # Refresh installment data
            installment.refresh_from_db()
            return Response({
                'message': 'Payment recorded successfully.',
                'remaining_amount': str(installment.remaining_amount),
                'is_completed': installment.is_completed
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PaymentRecordViewSet(viewsets.ModelViewSet):
    """ViewSet for PaymentRecord CRUD operations."""
    
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['payment_date', 'created_at']
    ordering = ['-payment_date']
    
    def get_queryset(self):
        queryset = PaymentRecord.objects.filter(
            installment_record__shopkeeper=self.request.user
        )
        # Filter by installment if provided
        installment_id = self.request.query_params.get('installment_record')
        if installment_id:
            queryset = queryset.filter(installment_record_id=installment_id)
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentRecordCreateSerializer
        return PaymentRecordSerializer

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent payments with customer info."""
        from datetime import timedelta
        from django.utils import timezone
        
        # Get payments from last 30 days, limit to 10
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        queryset = self.get_queryset().filter(
            payment_date__gte=thirty_days_ago
        ).select_related('installment_record__customer')[:10]
        
        payments = []
        for payment in queryset:
            payments.append({
                'id': str(payment.id),
                'customer_name': payment.installment_record.customer.name,
                'customer_id': str(payment.installment_record.customer.id),
                'amount': str(payment.amount_paid),
                'date': payment.payment_date.strftime('%Y-%m-%d'),
                'time_ago': self._get_time_ago(payment.payment_date),
            })
        
        return Response(payments)
    
    def _get_time_ago(self, date):
        """Get human-readable time ago string."""
        from datetime import datetime
        from django.utils import timezone
        
        today = timezone.now().date()
        diff = today - date
        
        if diff.days == 0:
            return 'Today'
        elif diff.days == 1:
            return 'Yesterday'
        elif diff.days < 7:
            return f'{diff.days} days ago'
        elif diff.days < 30:
            weeks = diff.days // 7
            return f'{weeks} week{"s" if weeks > 1 else ""} ago'
        else:
            months = diff.days // 30
            return f'{months} month{"s" if months > 1 else ""} ago'
