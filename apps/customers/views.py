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
    
    @action(detail=False, methods=['get'])
    def monthly_reports(self, request):
        """Get monthly and yearly payment reports."""
        from django.utils import timezone
        from django.db.models import Sum
        from django.db.models.functions import ExtractMonth, ExtractYear
        from datetime import date
        from calendar import month_name
        
        # Get year parameter (default to current year)
        year = request.query_params.get('year')
        if year:
            try:
                year = int(year)
            except ValueError:
                year = timezone.now().year
        else:
            year = timezone.now().year
        
        # Get all payments for this shopkeeper
        payments = self.get_queryset()
        
        # Current month stats
        today = timezone.now().date()
        
        current_month_payments = payments.filter(
            payment_date__year=today.year,
            payment_date__month=today.month
        ).aggregate(
            total=Sum('amount_paid'),
            count=Count('id')
        )
        
        # Year-to-date stats
        year_payments = payments.filter(
            payment_date__year=year
        ).aggregate(
            total=Sum('amount_paid'),
            count=Count('id')
        )
        
        # Monthly breakdown for the selected year - get all data
        monthly_data = payments.filter(
            payment_date__year=year
        ).annotate(
            month=ExtractMonth('payment_date')
        ).values('month').annotate(
            total=Sum('amount_paid'),
            count=Count('id')
        ).order_by('month')
        
        # Create a dict for easy lookup
        monthly_dict = {item['month']: item for item in monthly_data}
        
        # Build all 12 months
        monthly_breakdown = []
        for month_num in range(1, 13):
            if month_num in monthly_dict:
                item = monthly_dict[month_num]
                monthly_breakdown.append({
                    'month': month_num,
                    'month_name': month_name[month_num],
                    'total': str(item['total'] or 0),
                    'count': item['count']
                })
            else:
                monthly_breakdown.append({
                    'month': month_num,
                    'month_name': month_name[month_num],
                    'total': '0',
                    'count': 0
                })
        
        # Get available years (years with payments)
        available_years = payments.annotate(
            year=ExtractYear('payment_date')
        ).values('year').distinct().order_by('-year')
        
        years_list = [item['year'] for item in available_years if item['year']]
        if year not in years_list:
            years_list.insert(0, year)
        
        return Response({
            'selected_year': year,
            'available_years': sorted(years_list, reverse=True),
            'current_month': {
                'month_name': month_name[today.month],
                'month': today.month,
                'year': today.year,
                'total': str(current_month_payments['total'] or 0),
                'count': current_month_payments['count'] or 0
            },
            'year_to_date': {
                'year': year,
                'total': str(year_payments['total'] or 0),
                'count': year_payments['count'] or 0
            },
            'monthly_breakdown': monthly_breakdown
        })
    
    @action(detail=False, methods=['get'])
    def month_detail(self, request):
        """Get detailed payment data for a specific month."""
        from django.utils import timezone
        from django.db.models import Sum, Count
        from datetime import date
        from calendar import month_name
        
        # Get year and month parameters
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        
        if not year or not month:
            return Response({'error': 'Year and month parameters are required'}, status=400)
        
        try:
            year = int(year)
            month = int(month)
        except ValueError:
            return Response({'error': 'Invalid year or month'}, status=400)
        
        if month < 1 or month > 12:
            return Response({'error': 'Month must be between 1 and 12'}, status=400)
        
        # Get all payments for this month
        payments = self.get_queryset().filter(
            payment_date__year=year,
            payment_date__month=month
        ).select_related('installment_record__customer')
        
        # Summary stats
        total_paid = payments.aggregate(total=Sum('amount_paid'))['total'] or 0
        total_payments = payments.count()
        
        # Get unique customers who made payments this month
        customer_ids = payments.values_list(
            'installment_record__customer_id', flat=True
        ).distinct()
        
        # Get all installment records that had payments this month
        installment_ids = payments.values_list('installment_record_id', flat=True).distinct()
        
        # Get installment records
        from .models import InstallmentRecord, Customer
        installments = InstallmentRecord.objects.filter(
            id__in=installment_ids,
            shopkeeper=request.user
        ).select_related('customer')
        
        paid_installments = installments.filter(is_completed=True).count()
        pending_installments = installments.filter(is_completed=False).count()
        
        # Get remaining amount for pending installments
        total_remaining = installments.filter(is_completed=False).aggregate(
            total=Sum('remaining_amount')
        )['total'] or 0
        
        # Get customer details with their payments for this month
        customers_data = []
        unique_customers = Customer.objects.filter(
            id__in=customer_ids,
            shopkeeper=request.user
        )
        
        for customer in unique_customers:
            # Get payments for this customer in this month
            customer_payments = payments.filter(
                installment_record__customer=customer
            )
            
            customer_total_paid = customer_payments.aggregate(
                total=Sum('amount_paid')
            )['total'] or 0
            
            customer_payment_count = customer_payments.count()
            
            # Get customer's installments that had payments
            customer_installments = installments.filter(customer=customer)
            customer_remaining = customer_installments.filter(is_completed=False).aggregate(
                total=Sum('remaining_amount')
            )['total'] or 0
            
            customer_paid_installments = customer_installments.filter(is_completed=True).count()
            customer_pending_installments = customer_installments.filter(is_completed=False).count()
            
            # Get individual payment records
            payment_records = []
            for payment in customer_payments.order_by('-payment_date'):
                payment_records.append({
                    'id': str(payment.id),
                    'amount': str(payment.amount_paid),
                    'date': payment.payment_date.strftime('%Y-%m-%d'),
                    'product': payment.installment_record.product_name,
                    'notes': payment.notes or ''
                })
            
            customers_data.append({
                'id': str(customer.id),
                'name': customer.name,
                'mobile': customer.mobile_number,
                'total_paid': str(customer_total_paid),
                'payment_count': customer_payment_count,
                'remaining': str(customer_remaining),
                'paid_installments': customer_paid_installments,
                'pending_installments': customer_pending_installments,
                'payments': payment_records
            })
        
        # Sort customers by total paid (descending)
        customers_data.sort(key=lambda x: float(x['total_paid']), reverse=True)
        
        return Response({
            'year': year,
            'month': month,
            'month_name': month_name[month],
            'summary': {
                'total_paid': str(total_paid),
                'total_payments': total_payments,
                'total_customers': len(customer_ids),
                'paid_installments': paid_installments,
                'pending_installments': pending_installments,
                'total_remaining': str(total_remaining)
            },
            'customers': customers_data
        })
