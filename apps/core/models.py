"""
Core Models - Product, InstallmentPlan, and InstallmentPayment models
"""

from django.db import models
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
import uuid


class Product(models.Model):
    """
    Product model for items being sold on installments.
    """
    
    CATEGORY_CHOICES = (
        ('electronics', 'Electronics'),
        ('appliances', 'Home Appliances'),
        ('furniture', 'Furniture'),
        ('mobile', 'Mobile Phones'),
        ('vehicles', 'Vehicles'),
        ('jewelry', 'Jewelry'),
        ('clothing', 'Clothing'),
        ('other', 'Other'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shopkeeper = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='products',
        limit_choices_to={'user_type': 'shopkeeper'}
    )
    
    # Product Details
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='other')
    brand = models.CharField(max_length=100, blank=True, null=True)
    model = models.CharField(max_length=100, blank=True, null=True)
    sku = models.CharField(max_length=50, blank=True, null=True)
    
    # Pricing
    cost_price = models.DecimalField(max_digits=12, decimal_places=2)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Images
    image_1 = models.ImageField(upload_to='products/', blank=True, null=True)
    image_2 = models.ImageField(upload_to='products/', blank=True, null=True)
    image_3 = models.ImageField(upload_to='products/', blank=True, null=True)
    
    # Inventory
    stock_quantity = models.IntegerField(default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'products'
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['shopkeeper']),
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.selling_price}"


class InstallmentPlan(models.Model):
    """
    Installment Plan model representing a purchase agreement with payment schedule.
    """
    
    STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('overdue', 'Overdue'),
        ('defaulted', 'Defaulted'),
        ('cancelled', 'Cancelled'),
    )
    
    FREQUENCY_CHOICES = (
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-Weekly'),
        ('monthly', 'Monthly'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shopkeeper = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_installment_plans',
        limit_choices_to={'user_type': 'shopkeeper'}
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='installment_plans',
        limit_choices_to={'user_type': 'buyer'}
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='installment_plans'
    )
    
    # Plan Details
    plan_name = models.CharField(max_length=200, blank=True, null=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    down_payment = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    remaining_amount = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Installment Schedule
    number_of_installments = models.IntegerField()
    installment_amount = models.DecimalField(max_digits=12, decimal_places=2)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='monthly')
    
    # Dates
    start_date = models.DateField()
    end_date = models.DateField()
    next_due_date = models.DateField(blank=True, null=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    installments_paid = models.IntegerField(default=0)
    
    # Documents
    invoice_image = models.ImageField(upload_to='invoices/', blank=True, null=True)
    agreement_image = models.ImageField(upload_to='agreements/', blank=True, null=True)
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'installment_plans'
        verbose_name = 'Installment Plan'
        verbose_name_plural = 'Installment Plans'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['shopkeeper']),
            models.Index(fields=['buyer']),
            models.Index(fields=['status']),
            models.Index(fields=['next_due_date']),
        ]
    
    def __str__(self):
        return f"Plan {self.id} - {self.buyer.full_name} - {self.total_amount}"
    
    def save(self, *args, **kwargs):
        # Calculate remaining amount if not set
        if not self.remaining_amount:
            self.remaining_amount = self.total_amount - self.down_payment
        
        # Calculate installment amount if not set
        if not self.installment_amount and self.number_of_installments > 0:
            self.installment_amount = self.remaining_amount / self.number_of_installments
        
        super().save(*args, **kwargs)
    
    @property
    def total_paid(self):
        """Calculate total amount paid."""
        return self.payments.filter(
            status='verified'
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
    
    @property
    def is_overdue(self):
        """Check if the plan has overdue payments."""
        if self.next_due_date and self.status == 'active':
            return self.next_due_date < timezone.now().date()
        return False
    
    def update_status(self):
        """Update plan status based on payments."""
        if self.remaining_amount <= 0:
            self.status = 'completed'
        elif self.is_overdue:
            self.status = 'overdue'
        self.save()


class InstallmentPayment(models.Model):
    """
    Individual payment record for an installment plan.
    """
    
    STATUS_CHOICES = (
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    )
    
    PAYMENT_METHOD_CHOICES = (
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('mobile_wallet', 'Mobile Wallet'),
        ('cheque', 'Cheque'),
        ('other', 'Other'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    installment_plan = models.ForeignKey(
        InstallmentPlan,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    
    # Payment Details
    installment_number = models.IntegerField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cash')
    
    # Dates
    due_date = models.DateField()
    payment_date = models.DateTimeField(blank=True, null=True)
    
    # Proof of Payment
    payment_proof = models.ImageField(upload_to='payment_proofs/', blank=True, null=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_payments'
    )
    verified_at = models.DateTimeField(blank=True, null=True)
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'installment_payments'
        verbose_name = 'Installment Payment'
        verbose_name_plural = 'Installment Payments'
        ordering = ['installment_number']
        indexes = [
            models.Index(fields=['installment_plan']),
            models.Index(fields=['status']),
            models.Index(fields=['due_date']),
        ]
        unique_together = ['installment_plan', 'installment_number']
    
    def __str__(self):
        return f"Payment {self.installment_number} - {self.amount} - {self.status}"
    
    def verify_payment(self, verified_by):
        """Mark payment as verified and update the installment plan."""
        self.status = 'verified'
        self.verified_by = verified_by
        self.verified_at = timezone.now()
        self.payment_date = timezone.now()
        self.save()
        
        # Update installment plan
        plan = self.installment_plan
        plan.remaining_amount -= self.amount
        plan.installments_paid += 1
        
        # Calculate next due date
        remaining_payments = plan.payments.filter(status='pending').order_by('due_date')
        if remaining_payments.exists():
            plan.next_due_date = remaining_payments.first().due_date
        else:
            plan.next_due_date = None
        
        plan.update_status()
    
    def reject_payment(self, rejection_reason):
        """Mark payment as rejected."""
        self.status = 'rejected'
        self.rejection_reason = rejection_reason
        self.save()
