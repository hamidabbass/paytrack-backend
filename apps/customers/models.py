"""
Customer Models - Customer and Installment Payment Records
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import uuid


class Customer(models.Model):
    """
    Customer model - represents a person who has an installment plan with the shopkeeper.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shopkeeper = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='customers',
        limit_choices_to={'user_type': 'shopkeeper'}
    )
    
    # Customer Details
    name = models.CharField(max_length=200)
    father_name = models.CharField(max_length=200)
    mobile_number = models.CharField(max_length=20)
    address = models.TextField()
    
    # Optional fields
    cnic_number = models.CharField(max_length=20, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'customers'
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['shopkeeper']),
            models.Index(fields=['mobile_number']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.mobile_number}"
    
    @property
    def total_pending(self):
        """Calculate total pending amount across all installment records."""
        return self.installment_records.filter(
            is_completed=False
        ).aggregate(
            total=models.Sum('remaining_amount')
        )['total'] or Decimal('0.00')
    
    @property
    def active_installments_count(self):
        """Count of active installment records."""
        return self.installment_records.filter(is_completed=False).count()
    
    @property
    def total_monthly_installment(self):
        """Calculate remaining monthly installment due for the current month.
        
        This is: total expected monthly installments - payments made this month.
        """
        from django.db.models import Sum
        
        # Get current month's first and last day
        today = timezone.now().date()
        first_day_of_month = today.replace(day=1)
        
        # Get total monthly installment expected from all active records
        total_expected = self.installment_records.filter(
            is_completed=False
        ).aggregate(
            total=Sum('monthly_installment')
        )['total'] or Decimal('0.00')
        
        # Get payments made this month for active installment records
        payments_this_month = Decimal('0.00')
        active_records = self.installment_records.filter(is_completed=False)
        for record in active_records:
            record_payments = record.payments.filter(
                payment_date__gte=first_day_of_month,
                payment_date__lte=today
            ).aggregate(
                total=Sum('amount_paid')
            )['total'] or Decimal('0.00')
            payments_this_month += record_payments
        
        # Return remaining amount for this month (can't be negative)
        remaining = total_expected - payments_this_month
        return max(remaining, Decimal('0.00'))

    @property
    def paid_this_month(self):
        """Calculate total payments made in the current month."""
        from django.db.models import Sum
        
        today = timezone.now().date()
        first_day_of_month = today.replace(day=1)
        
        payments_this_month = Decimal('0.00')
        active_records = self.installment_records.filter(is_completed=False)
        for record in active_records:
            record_payments = record.payments.filter(
                payment_date__gte=first_day_of_month,
                payment_date__lte=today
            ).aggregate(
                total=Sum('amount_paid')
            )['total'] or Decimal('0.00')
            payments_this_month += record_payments
        
        return payments_this_month


class InstallmentRecord(models.Model):
    """
    Installment Record - tracks installment payments for a customer.
    """
    
    # Status Choices
    STATUS_ACTIVE = 'active'
    STATUS_COMPLETED = 'completed'
    STATUS_OVERDUE = 'overdue'
    STATUS_PAUSED = 'paused'
    
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_OVERDUE, 'Overdue'),
        (STATUS_PAUSED, 'Paused'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='installment_records'
    )
    shopkeeper = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='installment_records',
        limit_choices_to={'user_type': 'shopkeeper'}
    )
    
    # Product/Item details (optional)
    product_name = models.CharField(max_length=200, blank=True, null=True)
    product_description = models.TextField(blank=True, null=True)
    
    # Financial Details
    total_cost = models.DecimalField(max_digits=12, decimal_places=2)
    advance_payment = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    monthly_installment = models.DecimalField(max_digits=12, decimal_places=2)
    remaining_amount = models.DecimalField(max_digits=12, decimal_places=2)
    total_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Payment Plan Details
    start_date = models.DateField(default=timezone.now)
    default_period = models.IntegerField(default=12, help_text="Default installment period in months")
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Interest rate percentage")
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    is_completed = models.BooleanField(default=False)
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'installment_records'
        verbose_name = 'Installment Record'
        verbose_name_plural = 'Installment Records'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer']),
            models.Index(fields=['shopkeeper']),
            models.Index(fields=['is_completed']),
        ]
    
    def __str__(self):
        return f"{self.customer.name} - {self.total_cost} ({self.remaining_amount} remaining)"
    
    def save(self, *args, **kwargs):
        # Calculate remaining amount if not set
        if self.remaining_amount is None or self.pk is None:
            self.remaining_amount = self.total_cost - self.advance_payment
        
        # Check if completed
        if self.remaining_amount <= 0:
            self.remaining_amount = Decimal('0.00')
            self.is_completed = True
            self.status = self.STATUS_COMPLETED
        
        super().save(*args, **kwargs)
    
    @property
    def calculated_status(self):
        """Calculate the current status based on payments and dates."""
        if self.is_completed:
            return self.STATUS_COMPLETED
        
        if self.status == self.STATUS_PAUSED:
            return self.STATUS_PAUSED
        
        # Check if overdue (no payment in the last 30 days and remaining > 0)
        from datetime import timedelta
        last_payment = self.payments.order_by('-payment_date').first()
        
        if last_payment:
            days_since_payment = (timezone.now().date() - last_payment.payment_date).days
            if days_since_payment > 35:  # More than ~1 month without payment
                return self.STATUS_OVERDUE
        else:
            # No payments yet, check from start date
            days_since_start = (timezone.now().date() - self.start_date).days
            if days_since_start > 35 and self.remaining_amount > 0:
                return self.STATUS_OVERDUE
        
        return self.STATUS_ACTIVE
    
    @property
    def calculated_total_paid(self):
        """Calculate total amount paid."""
        payments = self.payments.aggregate(
            total=models.Sum('amount_paid')
        )['total'] or Decimal('0.00')
        return payments + self.advance_payment


class PaymentRecord(models.Model):
    """
    Individual payment record for an installment.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    installment_record = models.ForeignKey(
        InstallmentRecord,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    
    # Payment Details
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField()
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'payment_records'
        verbose_name = 'Payment Record'
        verbose_name_plural = 'Payment Records'
        ordering = ['-payment_date', '-created_at']
    
    def __str__(self):
        return f"{self.installment_record.customer.name} - {self.amount_paid} on {self.payment_date}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._update_installment()
    
    def delete(self, *args, **kwargs):
        installment = self.installment_record
        super().delete(*args, **kwargs)
        # Recalculate after deletion
        self._recalculate_installment(installment)
    
    def _update_installment(self):
        """Update remaining amount and total_paid in installment record."""
        installment = self.installment_record
        total_payments = installment.payments.aggregate(
            total=models.Sum('amount_paid')
        )['total'] or Decimal('0.00')
        
        installment.total_paid = total_payments + installment.advance_payment
        installment.remaining_amount = installment.total_cost - installment.advance_payment - total_payments
        
        if installment.remaining_amount <= 0:
            installment.remaining_amount = Decimal('0.00')
            installment.is_completed = True
        else:
            installment.is_completed = False
        
        installment.save()
    
    @staticmethod
    def _recalculate_installment(installment):
        """Recalculate installment after payment deletion."""
        total_payments = installment.payments.aggregate(
            total=models.Sum('amount_paid')
        )['total'] or Decimal('0.00')
        
        installment.total_paid = total_payments + installment.advance_payment
        installment.remaining_amount = installment.total_cost - installment.advance_payment - total_payments
        
        if installment.remaining_amount <= 0:
            installment.remaining_amount = Decimal('0.00')
            installment.is_completed = True
        else:
            installment.is_completed = False
        
        installment.save()
