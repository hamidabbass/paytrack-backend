"""
Daily Payment Reminder Command
Sends push notifications to shopkeepers about unpaid customers at 9 AM daily.
Run with: python manage.py send_daily_reminders
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal
import requests
import json

from apps.users.models import User
from apps.customers.models import Customer
from apps.notifications.models import Notification


class Command(BaseCommand):
    help = 'Send daily payment reminder notifications to shopkeepers at 9 AM'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Starting daily payment reminders...'))
        
        today = timezone.now().date()
        
        # Get all shopkeepers
        shopkeepers = User.objects.filter(user_type='shopkeeper', is_active=True)
        
        notifications_sent = 0
        
        for shopkeeper in shopkeepers:
            # Get unpaid customers for this shopkeeper
            customers = Customer.objects.filter(
                shopkeeper=shopkeeper,
                is_active=True
            ).prefetch_related('installment_records')
            
            unpaid_customers = []
            total_due = Decimal('0.00')
            
            for customer in customers:
                monthly_due = customer.total_monthly_installment
                if monthly_due > 0:
                    unpaid_customers.append({
                        'name': customer.name,
                        'amount': str(monthly_due)  # Convert Decimal to string for JSON
                    })
                    total_due += monthly_due
            
            if unpaid_customers:
                # Create in-app notification
                notification = Notification.objects.create(
                    user=shopkeeper,
                    title=f'Daily Payment Reminder',
                    message=f'{len(unpaid_customers)} customer(s) have unpaid installments totaling Rs. {total_due:,.0f} this month.',
                    notification_type='payment_due',
                    data={
                        'unpaid_count': len(unpaid_customers),
                        'total_due': str(total_due),  # Convert Decimal to string
                        'date': str(today),
                        'customers': unpaid_customers[:5],  # First 5 customers
                    }
                )
                
                # Send push notification if user has expo push token
                if shopkeeper.expo_push_token:
                    self.send_push_notification(
                        shopkeeper.expo_push_token,
                        'Daily Payment Reminder',
                        f'{len(unpaid_customers)} customer(s) pending - Rs. {total_due:,.0f} due this month',
                        {
                            'type': 'payment_reminder',
                            'unpaid_count': len(unpaid_customers),
                            'total_due': str(total_due),
                        }
                    )
                
                notifications_sent += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Sent reminder to {shopkeeper.email}: {len(unpaid_customers)} unpaid customers'
                    )
                )
            else:
                self.stdout.write(
                    self.style.NOTICE(f'No unpaid customers for {shopkeeper.email}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Daily reminders completed. {notifications_sent} notifications sent.')
        )

    def send_push_notification(self, expo_push_token, title, body, data=None):
        """Send push notification via Expo Push Notification Service."""
        try:
            message = {
                'to': expo_push_token,
                'sound': 'default',
                'title': title,
                'body': body,
                'data': data or {},
            }
            
            response = requests.post(
                'https://exp.host/--/api/v2/push/send',
                json=message,
                headers={
                    'Accept': 'application/json',
                    'Accept-Encoding': 'gzip, deflate',
                    'Content-Type': 'application/json',
                }
            )
            
            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS(f'Push notification sent successfully'))
            else:
                self.stdout.write(self.style.WARNING(f'Push notification failed: {response.text}'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error sending push notification: {str(e)}'))
