"""
User Serializers - Serializers for User, Shopkeeper, and Buyer models
"""

from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, ShopkeeperProfile, BuyerProfile, SupportTicket


class UserSerializer(serializers.ModelSerializer):
    """Base User serializer."""
    
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone', 'first_name', 'last_name',
            'full_name', 'user_type', 'profile_image', 'address',
            'city', 'is_active', 'is_verified', 'date_joined'
        ]
        read_only_fields = ['id', 'date_joined', 'is_verified']


class ShopkeeperProfileSerializer(serializers.ModelSerializer):
    """Serializer for Shopkeeper Profile."""
    
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = ShopkeeperProfile
        fields = [
            'id', 'user', 'business_name', 'business_type',
            'business_address', 'business_phone', 'cnic_front',
            'cnic_back', 'cnic_number', 'business_license',
            'default_installment_period', 'default_interest_rate',
            'payment_methods', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class BuyerProfileSerializer(serializers.ModelSerializer):
    """Serializer for Buyer Profile."""
    
    user = UserSerializer(read_only=True)
    shopkeeper_name = serializers.CharField(source='shopkeeper.full_name', read_only=True)
    total_pending_amount = serializers.ReadOnlyField()
    
    class Meta:
        model = BuyerProfile
        fields = [
            'id', 'user', 'shopkeeper', 'shopkeeper_name',
            'cnic_front', 'cnic_back', 'cnic_number',
            'occupation', 'monthly_income', 'reference_name',
            'reference_phone', 'credit_score', 'is_blacklisted',
            'total_pending_amount', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'credit_score', 'created_at', 'updated_at']


class ShopkeeperRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for Shopkeeper registration."""
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    business_name = serializers.CharField(required=True, max_length=200)
    business_type = serializers.CharField(required=False, max_length=100, allow_blank=True)
    
    class Meta:
        model = User
        fields = [
            'email', 'password', 'password_confirm', 'phone',
            'first_name', 'last_name', 'address', 'city',
            'business_name', 'business_type'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Passwords do not match.'
            })
        return attrs
    
    def create(self, validated_data):
        # Extract profile data
        business_name = validated_data.pop('business_name')
        business_type = validated_data.pop('business_type', '')
        validated_data.pop('password_confirm')
        
        # Create user
        user = User.objects.create_user(
            user_type='shopkeeper',
            **validated_data
        )
        
        # Create shopkeeper profile
        ShopkeeperProfile.objects.create(
            user=user,
            business_name=business_name,
            business_type=business_type
        )
        
        return user


class BuyerRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for Buyer registration (by Shopkeeper)."""
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    cnic_number = serializers.CharField(required=False, max_length=20, allow_blank=True)
    occupation = serializers.CharField(required=False, max_length=100, allow_blank=True)
    monthly_income = serializers.DecimalField(
        required=False,
        max_digits=12,
        decimal_places=2,
        allow_null=True
    )
    reference_name = serializers.CharField(required=False, max_length=200, allow_blank=True)
    reference_phone = serializers.CharField(required=False, max_length=20, allow_blank=True)
    
    class Meta:
        model = User
        fields = [
            'email', 'password', 'phone', 'first_name', 'last_name',
            'address', 'city', 'cnic_number', 'occupation',
            'monthly_income', 'reference_name', 'reference_phone'
        ]
    
    def create(self, validated_data):
        # Get the shopkeeper from context
        shopkeeper = self.context['request'].user
        
        # Extract profile data
        cnic_number = validated_data.pop('cnic_number', '')
        occupation = validated_data.pop('occupation', '')
        monthly_income = validated_data.pop('monthly_income', None)
        reference_name = validated_data.pop('reference_name', '')
        reference_phone = validated_data.pop('reference_phone', '')
        
        # Create user
        user = User.objects.create_user(
            user_type='buyer',
            **validated_data
        )
        
        # Create buyer profile
        BuyerProfile.objects.create(
            user=user,
            shopkeeper=shopkeeper,
            cnic_number=cnic_number,
            occupation=occupation,
            monthly_income=monthly_income,
            reference_name=reference_name,
            reference_phone=reference_phone
        )
        
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""
    
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        user = authenticate(
            request=self.context.get('request'),
            email=email,
            password=password
        )
        
        if not user:
            raise serializers.ValidationError({
                'detail': 'Invalid email or password.'
            })
        
        if not user.is_active:
            raise serializers.ValidationError({
                'detail': 'User account is disabled.'
            })
        
        attrs['user'] = user
        return attrs


class TokenResponseSerializer(serializers.Serializer):
    """Serializer for token response."""
    
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()
    profile = serializers.SerializerMethodField()
    
    def get_profile(self, obj):
        user = obj['user']
        if user.user_type == 'shopkeeper':
            profile = getattr(user, 'shopkeeper_profile', None)
            if profile:
                return ShopkeeperProfileSerializer(profile).data
        elif user.user_type == 'buyer':
            profile = getattr(user, 'buyer_profile', None)
            if profile:
                return BuyerProfileSerializer(profile).data
        return None


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change."""
    
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password]
    )
    new_password_confirm = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': 'New passwords do not match.'
            })
        return attrs
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Old password is incorrect.')
        return value


class UpdateProfileSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile."""
    
    class Meta:
        model = User
        fields = [
            'phone', 'first_name', 'last_name',
            'profile_image', 'address', 'city'
        ]


class FCMTokenSerializer(serializers.Serializer):
    """Serializer for updating FCM token."""
    
    fcm_token = serializers.CharField(required=True, max_length=500)


class SupportTicketSerializer(serializers.ModelSerializer):
    """Serializer for Support Tickets."""
    
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    
    class Meta:
        model = SupportTicket
        fields = [
            'id', 'user', 'user_email', 'user_name',
            'category', 'subject', 'message', 'status',
            'response', 'responded_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'status', 'response', 'responded_at', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
