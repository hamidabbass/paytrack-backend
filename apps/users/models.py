"""
User Models - Custom User, Shopkeeper, and Buyer models
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
import uuid


class UserManager(BaseUserManager):
    """Custom user manager for User model."""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user with an email and password."""
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser with an email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('user_type', 'admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model supporting email authentication and multiple user types.
    """
    
    USER_TYPE_CHOICES = (
        ('shopkeeper', 'Shopkeeper'),
        ('buyer', 'Buyer'),
        ('admin', 'Admin'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, max_length=255)
    phone = models.CharField(max_length=20, blank=True, null=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    
    # Profile fields
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    
    # Status fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    
    # Timestamps
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # FCM Token for push notifications
    fcm_token = models.CharField(max_length=500, blank=True, null=True)
    
    # Expo Push Token for mobile app notifications
    expo_push_token = models.CharField(max_length=500, blank=True, null=True)
    
    # Notification Settings
    notification_settings = models.JSONField(default=dict, blank=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['user_type']),
            models.Index(fields=['phone']),
        ]
    
    def __str__(self):
        return f"{self.email} ({self.user_type})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_shopkeeper(self):
        return self.user_type == 'shopkeeper'
    
    @property
    def is_buyer(self):
        return self.user_type == 'buyer'


class ShopkeeperProfile(models.Model):
    """
    Extended profile for Shopkeeper users.
    Contains business-related information.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='shopkeeper_profile'
    )
    
    # Business Information
    business_name = models.CharField(max_length=200)
    business_type = models.CharField(max_length=100, blank=True, null=True)
    business_address = models.TextField(blank=True, null=True)
    business_phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Documents
    cnic_front = models.ImageField(upload_to='documents/cnic/', blank=True, null=True)
    cnic_back = models.ImageField(upload_to='documents/cnic/', blank=True, null=True)
    cnic_number = models.CharField(max_length=20, blank=True, null=True)
    business_license = models.ImageField(upload_to='documents/licenses/', blank=True, null=True)
    
    # Settings
    default_installment_period = models.IntegerField(default=12)  # months
    default_interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    # Payment Methods (JSON field to store enabled payment methods)
    payment_methods = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'shopkeeper_profiles'
        verbose_name = 'Shopkeeper Profile'
        verbose_name_plural = 'Shopkeeper Profiles'
    
    def __str__(self):
        return f"{self.business_name} - {self.user.email}"


class BuyerProfile(models.Model):
    """
    Extended profile for Buyer users.
    Contains buyer-specific information and links to their shopkeeper.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='buyer_profile'
    )
    shopkeeper = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='buyers',
        limit_choices_to={'user_type': 'shopkeeper'}
    )
    
    # Personal Documents
    cnic_front = models.ImageField(upload_to='documents/buyer_cnic/', blank=True, null=True)
    cnic_back = models.ImageField(upload_to='documents/buyer_cnic/', blank=True, null=True)
    cnic_number = models.CharField(max_length=20, blank=True, null=True)
    
    # Additional Information
    occupation = models.CharField(max_length=100, blank=True, null=True)
    monthly_income = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    reference_name = models.CharField(max_length=200, blank=True, null=True)
    reference_phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Status
    credit_score = models.IntegerField(default=100)  # Internal credit score
    is_blacklisted = models.BooleanField(default=False)
    blacklist_reason = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'buyer_profiles'
        verbose_name = 'Buyer Profile'
        verbose_name_plural = 'Buyer Profiles'
        indexes = [
            models.Index(fields=['shopkeeper']),
            models.Index(fields=['is_blacklisted']),
        ]
    
    def __str__(self):
        return f"{self.user.full_name} - Buyer of {self.shopkeeper.email}"
    
    @property
    def total_pending_amount(self):
        """Calculate total pending amount across all installment plans."""
        from apps.core.models import InstallmentPlan
        return InstallmentPlan.objects.filter(
            buyer=self.user,
            status__in=['active', 'overdue']
        ).aggregate(
            total=models.Sum('remaining_amount')
        )['total'] or 0


class SupportTicket(models.Model):
    """
    Support ticket model for user inquiries and issues.
    """
    
    CATEGORY_CHOICES = (
        ('technical', 'Technical Issue'),
        ('payment', 'Payment Problem'),
        ('account', 'Account Issue'),
        ('feature', 'Feature Request'),
        ('other', 'Other'),
    )
    
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='support_tickets'
    )
    
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    # Admin response
    response = models.TextField(blank=True, null=True)
    responded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='responded_tickets'
    )
    responded_at = models.DateTimeField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'support_tickets'
        verbose_name = 'Support Ticket'
        verbose_name_plural = 'Support Tickets'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.subject} - {self.user.email}"
