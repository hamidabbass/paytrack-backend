"""
Serializers for Customer, InstallmentRecord, and PaymentRecord
"""

from rest_framework import serializers
from django.db import models
from .models import Customer, InstallmentRecord, PaymentRecord


class PaymentRecordSerializer(serializers.ModelSerializer):
    """Serializer for PaymentRecord model."""
    
    remaining_after_payment = serializers.SerializerMethodField()
    total_paid_after_payment = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentRecord
        fields = [
            'id', 'installment_record', 'amount_paid', 'payment_date',
            'notes', 'remaining_after_payment', 'total_paid_after_payment', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_remaining_after_payment(self, obj):
        """Calculate remaining amount after this payment."""
        # Get all payments up to and including this one
        payments_before = obj.installment_record.payments.filter(
            created_at__lte=obj.created_at
        ).aggregate(total=models.Sum('amount_paid'))['total'] or 0
        
        remaining = obj.installment_record.total_cost - obj.installment_record.advance_payment - payments_before
        return str(max(remaining, 0))
    
    def get_total_paid_after_payment(self, obj):
        """Calculate total paid after this payment."""
        payments_before = obj.installment_record.payments.filter(
            created_at__lte=obj.created_at
        ).aggregate(total=models.Sum('amount_paid'))['total'] or 0
        
        return str(payments_before + obj.installment_record.advance_payment)


class PaymentRecordCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating PaymentRecord."""
    
    class Meta:
        model = PaymentRecord
        fields = ['installment_record', 'amount_paid', 'payment_date', 'notes']
    
    def validate_amount_paid(self, value):
        if value <= 0:
            raise serializers.ValidationError("Payment amount must be greater than zero.")
        return value


class InstallmentRecordSerializer(serializers.ModelSerializer):
    """Serializer for InstallmentRecord model."""
    
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_mobile = serializers.CharField(source='customer.mobile_number', read_only=True)
    payments = PaymentRecordSerializer(many=True, read_only=True)
    payments_count = serializers.SerializerMethodField()
    calculated_status = serializers.CharField(read_only=True)
    status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = InstallmentRecord
        fields = [
            'id', 'customer', 'customer_name', 'customer_mobile', 'shopkeeper',
            'product_name', 'product_description', 'total_cost', 'advance_payment',
            'monthly_installment', 'remaining_amount', 'total_paid', 'start_date',
            'default_period', 'interest_rate', 'status', 'calculated_status', 
            'status_display', 'is_completed', 'notes',
            'payments', 'payments_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'shopkeeper', 'remaining_amount', 'total_paid', 'is_completed', 'created_at', 'updated_at']
    
    def get_payments_count(self, obj):
        return obj.payments.count()
    
    def get_status_display(self, obj):
        """Return human-readable status."""
        status = obj.calculated_status
        status_map = {
            'active': 'Active',
            'completed': 'Completed',
            'overdue': 'Overdue',
            'paused': 'Paused',
        }
        return status_map.get(status, 'Unknown')


class InstallmentRecordCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating InstallmentRecord."""
    
    class Meta:
        model = InstallmentRecord
        fields = [
            'customer', 'product_name', 'product_description', 'total_cost',
            'advance_payment', 'monthly_installment', 'start_date', 'default_period',
            'interest_rate', 'notes'
        ]
    
    def validate(self, data):
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Validating installment data: {data}")
        
        if data.get('advance_payment', 0) >= data['total_cost']:
            raise serializers.ValidationError("Advance payment cannot be greater than or equal to total cost.")
        if data['monthly_installment'] <= 0:
            raise serializers.ValidationError("Monthly installment must be greater than zero.")
        return data
    
    def create(self, validated_data):
        validated_data['shopkeeper'] = self.context['request'].user
        validated_data['remaining_amount'] = validated_data['total_cost'] - validated_data.get('advance_payment', 0)
        validated_data['total_paid'] = validated_data.get('advance_payment', 0)
        return super().create(validated_data)


class CustomerSerializer(serializers.ModelSerializer):
    """Serializer for Customer model."""
    
    total_pending = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    active_installments_count = serializers.IntegerField(read_only=True)
    installment_records = InstallmentRecordSerializer(many=True, read_only=True)
    
    class Meta:
        model = Customer
        fields = [
            'id', 'shopkeeper', 'name', 'father_name', 'mobile_number', 'address',
            'cnic_number', 'notes', 'is_active', 'total_pending', 'active_installments_count',
            'installment_records', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'shopkeeper', 'created_at', 'updated_at']


class CustomerListSerializer(serializers.ModelSerializer):
    """Simplified serializer for Customer list view."""
    
    total_pending = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_monthly_installment = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    paid_this_month = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    active_installments_count = serializers.IntegerField(read_only=True)
    customer_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'father_name', 'mobile_number', 'address',
            'is_active', 'total_pending', 'total_monthly_installment', 'paid_this_month',
            'active_installments_count', 'customer_status', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_customer_status(self, obj):
        """Get overall customer status based on their installments."""
        installments = obj.installment_records.all()
        
        if not installments.exists():
            return {'status': 'none', 'label': 'No Plans'}
        
        # Check for overdue
        for inst in installments:
            if inst.calculated_status == 'overdue':
                return {'status': 'overdue', 'label': 'Overdue'}
        
        # Check if all completed
        active_count = installments.filter(is_completed=False).count()
        if active_count == 0:
            return {'status': 'completed', 'label': 'Completed'}
        
        # Has active installments
        return {'status': 'active', 'label': f'{active_count} Active'}


class CustomerCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Customer."""
    
    class Meta:
        model = Customer
        fields = ['id', 'name', 'father_name', 'mobile_number', 'address', 'cnic_number', 'notes']
        read_only_fields = ['id']
    
    def validate_mobile_number(self, value):
        if len(value) < 10:
            raise serializers.ValidationError("Mobile number must be at least 10 digits.")
        return value
    
    def create(self, validated_data):
        validated_data['shopkeeper'] = self.context['request'].user
        return super().create(validated_data)
