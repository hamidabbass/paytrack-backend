"""
Dashboard Views - Shopkeeper dashboard endpoints
"""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta

from apps.users.models import BuyerProfile
from apps.core.models import InstallmentPlan, InstallmentPayment, Product
from apps.core.permissions import IsShopkeeper


class ShopkeeperDashboardView(APIView):
    """
    Get shopkeeper dashboard statistics.
    GET /api/core/dashboard/
    """
    permission_classes = [IsAuthenticated, IsShopkeeper]
    
    def get(self, request):
        user = request.user
        
        # Get total buyers count
        total_buyers = BuyerProfile.objects.filter(
            shopkeeper=user
        ).count()
        
        # Get active plans count
        active_plans = InstallmentPlan.objects.filter(
            shopkeeper=user,
            status='active'
        ).count()
        
        # Get pending payments count
        pending_payments = InstallmentPayment.objects.filter(
            installment_plan__shopkeeper=user,
            status='pending'
        ).count()
        
        # Get total revenue (verified payments)
        total_revenue = InstallmentPayment.objects.filter(
            installment_plan__shopkeeper=user,
            status='verified'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Get overdue payments
        today = timezone.now().date()
        overdue_payments = InstallmentPayment.objects.filter(
            installment_plan__shopkeeper=user,
            status='pending',
            due_date__lt=today
        ).count()
        
        # Get recent activities
        recent_activities = []
        
        # Recent payments
        recent_payments = InstallmentPayment.objects.filter(
            installment_plan__shopkeeper=user
        ).select_related(
            'installment_plan__buyer'
        ).order_by('-created_at')[:5]
        
        for payment in recent_payments:
            buyer_name = payment.installment_plan.buyer.full_name if payment.installment_plan.buyer else 'Unknown'
            if payment.status == 'verified':
                recent_activities.append({
                    'icon': '✅',
                    'title': f'Payment verified',
                    'description': f'Rs. {payment.amount} from {buyer_name}',
                    'time': self.get_time_ago(payment.updated_at)
                })
            elif payment.status == 'pending':
                recent_activities.append({
                    'icon': '⏳',
                    'title': f'Payment pending',
                    'description': f'Rs. {payment.amount} from {buyer_name}',
                    'time': self.get_time_ago(payment.created_at)
                })
        
        # Get upcoming payments (next 7 days)
        next_week = today + timedelta(days=7)
        upcoming_payments = InstallmentPayment.objects.filter(
            installment_plan__shopkeeper=user,
            status='pending',
            due_date__gte=today,
            due_date__lte=next_week
        ).select_related(
            'installment_plan__buyer'
        ).order_by('due_date')[:5]
        
        upcoming_list = []
        for payment in upcoming_payments:
            buyer_name = payment.installment_plan.buyer.full_name if payment.installment_plan.buyer else 'Unknown'
            upcoming_list.append({
                'id': str(payment.id),
                'buyer_name': buyer_name,
                'amount': str(payment.amount),
                'due_date': payment.due_date.isoformat(),
                'days_until_due': (payment.due_date - today).days
            })
        
        return Response({
            'success': True,
            'data': {
                'total_buyers': total_buyers,
                'active_plans': active_plans,
                'pending_payments': pending_payments,
                'overdue_payments': overdue_payments,
                'total_revenue': float(total_revenue),
                'recent_activities': recent_activities[:10],
                'upcoming_payments': upcoming_list
            }
        })
    
    def get_time_ago(self, dt):
        """Convert datetime to human-readable time ago string."""
        if not dt:
            return ''
        
        now = timezone.now()
        diff = now - dt
        
        if diff.days > 0:
            if diff.days == 1:
                return '1 day ago'
            return f'{diff.days} days ago'
        
        hours = diff.seconds // 3600
        if hours > 0:
            if hours == 1:
                return '1 hour ago'
            return f'{hours} hours ago'
        
        minutes = diff.seconds // 60
        if minutes > 0:
            if minutes == 1:
                return '1 minute ago'
            return f'{minutes} minutes ago'
        
        return 'Just now'
