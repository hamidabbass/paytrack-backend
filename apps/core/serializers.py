"""
Core Serializers - Serializers for Product, InstallmentPlan, and InstallmentPayment
"""

from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from .models import Product, InstallmentPlan, InstallmentPayment
from apps.users.serializers import UserSerializer


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for Product model."""
    
    shopkeeper_name = serializers.CharField(source='shopkeeper.full_name', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'shopkeeper', 'shopkeeper_name', 'name', 'description',
            'category', 'brand', 'model', 'sku', 'cost_price',
            'selling_price', 'image_1', 'image_2', 'image_3',
            'stock_quantity', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'shopkeeper', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        validated_data['shopkeeper'] = self.context['request'].user
        return super().create(validated_data)


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for product listing."""
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'category', 'selling_price',
            'image_1', 'stock_quantity', 'is_active'
        ]


class InstallmentPaymentSerializer(serializers.ModelSerializer):
    """Serializer for InstallmentPayment model."""
    
    verified_by_name = serializers.CharField(source='verified_by.full_name', read_only=True)
    is_overdue = serializers.SerializerMethodField()
    
    class Meta:
        model = InstallmentPayment
        fields = [
            'id', 'installment_plan', 'installment_number', 'amount',
            'payment_method', 'due_date', 'payment_date', 'payment_proof',
            'transaction_id', 'status', 'verified_by', 'verified_by_name',
            'verified_at', 'notes', 'rejection_reason', 'is_overdue',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'installment_plan', 'installment_number', 'amount',
            'due_date', 'verified_by', 'verified_at', 'created_at', 'updated_at'
        ]
    
    def get_is_overdue(self, obj):
        if obj.status == 'pending' and obj.due_date:
            return obj.due_date < timezone.now().date()
        return False


class InstallmentPaymentCreateSerializer(serializers.Serializer):
    """Serializer for creating payment proof submission."""
    
    payment_proof = serializers.ImageField(required=True)
    payment_method = serializers.ChoiceField(
        choices=InstallmentPayment.PAYMENT_METHOD_CHOICES,
        default='cash'
    )
    transaction_id = serializers.CharField(required=False, allow_blank=True, max_length=100)
    notes = serializers.CharField(required=False, allow_blank=True)


class InstallmentPaymentVerifySerializer(serializers.Serializer):
    """Serializer for verifying a payment."""
    
    action = serializers.ChoiceField(choices=['verify', 'reject'])
    rejection_reason = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        if attrs['action'] == 'reject' and not attrs.get('rejection_reason'):
            raise serializers.ValidationError({
                'rejection_reason': 'Rejection reason is required when rejecting a payment.'
            })
        return attrs


class InstallmentPlanSerializer(serializers.ModelSerializer):
    """Serializer for InstallmentPlan model."""
    
    shopkeeper_name = serializers.CharField(source='shopkeeper.full_name', read_only=True)
    buyer_name = serializers.CharField(source='buyer.full_name', read_only=True)
    buyer_phone = serializers.CharField(source='buyer.phone', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    total_paid = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    payments = InstallmentPaymentSerializer(many=True, read_only=True)
    
    class Meta:
        model = InstallmentPlan
        fields = [
            'id', 'shopkeeper', 'shopkeeper_name', 'buyer', 'buyer_name',
            'buyer_phone', 'product', 'product_name', 'plan_name',
            'total_amount', 'down_payment', 'remaining_amount',
            'interest_rate', 'number_of_installments', 'installment_amount',
            'frequency', 'start_date', 'end_date', 'next_due_date',
            'status', 'installments_paid', 'invoice_image', 'agreement_image',
            'notes', 'total_paid', 'is_overdue', 'payments',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'shopkeeper', 'remaining_amount', 'installment_amount',
            'end_date', 'next_due_date', 'installments_paid', 'total_paid',
            'created_at', 'updated_at'
        ]


class InstallmentPlanListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for installment plan listing."""
    
    buyer_name = serializers.CharField(source='buyer.full_name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    total_paid = serializers.ReadOnlyField()
    
    class Meta:
        model = InstallmentPlan
        fields = [
            'id', 'buyer', 'buyer_name', 'product_name', 'total_amount',
            'remaining_amount', 'installment_amount', 'next_due_date',
            'status', 'installments_paid', 'number_of_installments',
            'total_paid', 'created_at'
        ]


class InstallmentPlanCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new installment plan."""
    
    class Meta:
        model = InstallmentPlan
        fields = [
            'buyer', 'product', 'plan_name', 'total_amount',
            'down_payment', 'interest_rate', 'number_of_installments',
            'frequency', 'start_date', 'invoice_image', 'agreement_image', 'notes'
        ]
    
    def validate_buyer(self, value):
        """Validate that the buyer belongs to the shopkeeper."""
        request = self.context['request']
        if value.user_type != 'buyer':
            raise serializers.ValidationError('Selected user is not a buyer.')
        
        buyer_profile = getattr(value, 'buyer_profile', None)
        if not buyer_profile or buyer_profile.shopkeeper != request.user:
            raise serializers.ValidationError('This buyer does not belong to you.')
        
        return value
    
    def validate_product(self, value):
        """Validate that the product belongs to the shopkeeper."""
        if value:
            request = self.context['request']
            if value.shopkeeper != request.user:
                raise serializers.ValidationError('This product does not belong to you.')
        return value
    
    def create(self, validated_data):
        request = self.context['request']
        shopkeeper = request.user
        
        # Calculate values
        total_amount = validated_data['total_amount']
        down_payment = validated_data.get('down_payment', 0)
        interest_rate = validated_data.get('interest_rate', 0)
        number_of_installments = validated_data['number_of_installments']
        frequency = validated_data.get('frequency', 'monthly')
        start_date = validated_data['start_date']
        
        # Calculate remaining amount with interest
        principal = total_amount - down_payment
        interest = principal * (interest_rate / 100)
        remaining_amount = principal + interest
        installment_amount = remaining_amount / number_of_installments
        
        # Calculate end date
        if frequency == 'weekly':
            end_date = start_date + timedelta(weeks=number_of_installments)
        elif frequency == 'biweekly':
            end_date = start_date + timedelta(weeks=number_of_installments * 2)
        else:  # monthly
            end_date = start_date + relativedelta(months=number_of_installments)
        
        # Create installment plan
        plan = InstallmentPlan.objects.create(
            shopkeeper=shopkeeper,
            remaining_amount=remaining_amount,
            installment_amount=round(installment_amount, 2),
            end_date=end_date,
            next_due_date=start_date,
            status='active',
            **validated_data
        )
        
        # Create individual payment records
        current_date = start_date
        for i in range(1, number_of_installments + 1):
            InstallmentPayment.objects.create(
                installment_plan=plan,
                installment_number=i,
                amount=round(installment_amount, 2),
                due_date=current_date
            )
            
            if frequency == 'weekly':
                current_date = current_date + timedelta(weeks=1)
            elif frequency == 'biweekly':
                current_date = current_date + timedelta(weeks=2)
            else:  # monthly
                current_date = current_date + relativedelta(months=1)
        
        return plan


class BuyerInstallmentSummarySerializer(serializers.Serializer):
    """Serializer for buyer's installment summary."""
    
    total_plans = serializers.IntegerField()
    active_plans = serializers.IntegerField()
    completed_plans = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_paid = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_pending = serializers.DecimalField(max_digits=12, decimal_places=2)
    next_payment_date = serializers.DateField(allow_null=True)
    next_payment_amount = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
