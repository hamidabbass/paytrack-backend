"""
Notification Views
API views for notification management
"""

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal

from .models import Notification
from .serializers import NotificationSerializer, MarkNotificationReadSerializer


class NotificationListView(generics.ListAPIView):
    """List all notifications for the authenticated user."""
    
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        unread_count = queryset.filter(is_read=False).count()
        
        # Paginate
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data['unread_count'] = unread_count
            return response
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'unread_count': unread_count
        })


class NotificationDetailView(generics.RetrieveDestroyAPIView):
    """Retrieve or delete a specific notification."""
    
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Mark as read when viewed
        if not instance.is_read:
            instance.mark_as_read()
        serializer = self.get_serializer(instance)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({
            'success': True,
            'message': 'Notification deleted'
        }, status=status.HTTP_200_OK)


class MarkNotificationsReadView(APIView):
    """Mark notifications as read."""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = MarkNotificationReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        queryset = Notification.objects.filter(user=request.user, is_read=False)
        
        if serializer.validated_data.get('mark_all'):
            # Mark all as read
            count = queryset.update(is_read=True, read_at=timezone.now())
        else:
            # Mark specific notifications as read
            notification_ids = serializer.validated_data.get('notification_ids', [])
            if notification_ids:
                count = queryset.filter(id__in=notification_ids).update(
                    is_read=True, read_at=timezone.now()
                )
            else:
                count = 0
        
        return Response({
            'success': True,
            'message': f'{count} notifications marked as read',
            'count': count
        })


class UnreadCountView(APIView):
    """Get unread notification count."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        count = Notification.objects.filter(
            user=request.user, 
            is_read=False
        ).count()
        
        return Response({
            'success': True,
            'unread_count': count
        })


class ClearAllNotificationsView(APIView):
    """Clear all notifications for the user."""
    
    permission_classes = [IsAuthenticated]
    
    def delete(self, request):
        count = Notification.objects.filter(user=request.user).delete()[0]
        return Response({
            'success': True,
            'message': f'{count} notifications cleared',
            'count': count
        })


class GeneratePaymentRemindersView(APIView):
    """Generate payment reminder notifications for unpaid customers."""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        from apps.customers.models import Customer
        
        user = request.user
        today = timezone.now().date()
        first_day_of_month = today.replace(day=1)
        
        # Get all customers with unpaid installments this month
        customers = Customer.objects.filter(
            shopkeeper=user,
            is_active=True
        ).prefetch_related('installment_records')
        
        reminders_created = 0
        reminders_data = []
        
        for customer in customers:
            # Check if customer has unpaid amount this month
            monthly_due = customer.total_monthly_installment
            
            if monthly_due > 0:
                # Check if a reminder was already sent today for this customer
                existing_reminder = Notification.objects.filter(
                    user=user,
                    notification_type='payment_due',
                    reference_id=customer.id,
                    created_at__date=today
                ).exists()
                
                if not existing_reminder:
                    # Create payment reminder notification
                    notification = Notification.objects.create(
                        user=user,
                        title=f'Payment Due: {customer.name}',
                        message=f'Rs. {monthly_due:,.0f} pending for this month. Total remaining: Rs. {customer.total_pending:,.0f}',
                        notification_type='payment_due',
                        reference_id=customer.id,
                        reference_type='customer',
                        data={
                            'customer_name': customer.name,
                            'customer_phone': customer.mobile_number,
                            'monthly_due': str(monthly_due),
                            'total_pending': str(customer.total_pending),
                        }
                    )
                    reminders_created += 1
                    reminders_data.append({
                        'customer_name': customer.name,
                        'amount_due': str(monthly_due)
                    })
        
        return Response({
            'success': True,
            'message': f'{reminders_created} payment reminders generated',
            'count': reminders_created,
            'reminders': reminders_data
        })


class GetPaymentRemindersView(APIView):
    """Get payment reminders for unpaid customers (without creating notifications)."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from apps.customers.models import Customer
        
        user = request.user
        today = timezone.now().date()
        
        # Get all customers with unpaid installments this month
        customers = Customer.objects.filter(
            shopkeeper=user,
            is_active=True
        ).prefetch_related('installment_records')
        
        reminders = []
        
        for customer in customers:
            monthly_due = customer.total_monthly_installment
            
            if monthly_due > 0:
                # Get the latest active installment record
                latest_record = customer.installment_records.filter(
                    is_completed=False
                ).order_by('-created_at').first()
                
                # Calculate days since last payment
                days_overdue = 0
                if latest_record:
                    last_payment = latest_record.payments.order_by('-payment_date').first()
                    if last_payment:
                        days_overdue = (today - last_payment.payment_date).days
                    else:
                        days_overdue = (today - latest_record.start_date).days
                
                reminders.append({
                    'id': str(customer.id),
                    'customer_name': customer.name,
                    'customer_phone': customer.mobile_number,
                    'monthly_due': str(monthly_due),
                    'total_pending': str(customer.total_pending),
                    'days_overdue': days_overdue,
                    'status': 'overdue' if days_overdue > 30 else 'due',
                    'paid_this_month': str(customer.paid_this_month),
                })
        
        # Sort by days overdue (most overdue first)
        reminders.sort(key=lambda x: x['days_overdue'], reverse=True)
        
        return Response({
            'success': True,
            'data': reminders,
            'count': len(reminders)
        })


# Utility function to create notifications (can be called from other apps)
def create_notification(
    user,
    title,
    message,
    notification_type='system',
    reference_id=None,
    reference_type=None,
    data=None
):
    """
    Helper function to create a notification.
    Can be imported and used from other apps.
    """
    return Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
        reference_id=reference_id,
        reference_type=reference_type,
        data=data or {}
    )
