"""
Chat Serializers - Serializers for Conversation and Message models
"""

from rest_framework import serializers
from .models import Conversation, Message
from apps.users.serializers import UserSerializer


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for Message model."""
    
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    sender_image = serializers.ImageField(source='sender.profile_image', read_only=True)
    
    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'sender_name', 'sender_image',
            'receiver', 'message_type', 'message_text', 'image',
            'voice_note', 'voice_duration', 'document', 'document_name',
            'is_read', 'read_at', 'created_at'
        ]
        read_only_fields = ['id', 'conversation', 'sender', 'receiver', 'created_at']


class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new message."""
    
    class Meta:
        model = Message
        fields = [
            'message_type', 'message_text', 'image',
            'voice_note', 'voice_duration', 'document', 'document_name'
        ]
    
    def validate(self, attrs):
        message_type = attrs.get('message_type', 'text')
        
        if message_type == 'text' and not attrs.get('message_text'):
            raise serializers.ValidationError({
                'message_text': 'Text message requires message_text.'
            })
        elif message_type == 'image' and not attrs.get('image'):
            raise serializers.ValidationError({
                'image': 'Image message requires an image.'
            })
        elif message_type == 'voice' and not attrs.get('voice_note'):
            raise serializers.ValidationError({
                'voice_note': 'Voice message requires a voice_note.'
            })
        elif message_type == 'document' and not attrs.get('document'):
            raise serializers.ValidationError({
                'document': 'Document message requires a document.'
            })
        
        return attrs


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for Conversation model."""
    
    shopkeeper_info = UserSerializer(source='shopkeeper', read_only=True)
    buyer_info = UserSerializer(source='buyer', read_only=True)
    last_message_sender_name = serializers.CharField(
        source='last_message_sender.full_name',
        read_only=True
    )
    unread_count = serializers.SerializerMethodField()
    other_user = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'shopkeeper', 'shopkeeper_info', 'buyer', 'buyer_info',
            'last_message', 'last_message_at', 'last_message_sender',
            'last_message_sender_name', 'unread_count', 'other_user',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'last_message', 'last_message_at', 'last_message_sender',
            'created_at', 'updated_at'
        ]
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.get_unread_count(request.user)
        return 0
    
    def get_other_user(self, obj):
        request = self.context.get('request')
        if request and request.user:
            if request.user == obj.shopkeeper:
                return UserSerializer(obj.buyer).data
            else:
                return UserSerializer(obj.shopkeeper).data
        return None


class ConversationCreateSerializer(serializers.Serializer):
    """Serializer for creating or getting a conversation."""
    
    buyer_id = serializers.UUIDField(required=True)
    
    def validate_buyer_id(self, value):
        from apps.users.models import User
        try:
            buyer = User.objects.get(id=value, user_type='buyer')
        except User.DoesNotExist:
            raise serializers.ValidationError('Buyer not found.')
        
        # Check if buyer belongs to the shopkeeper
        request = self.context['request']
        buyer_profile = getattr(buyer, 'buyer_profile', None)
        if not buyer_profile or buyer_profile.shopkeeper != request.user:
            raise serializers.ValidationError('This buyer does not belong to you.')
        
        return value


class ConversationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for conversation listing."""
    
    other_user_name = serializers.SerializerMethodField()
    other_user_image = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'other_user_name', 'other_user_image',
            'last_message', 'last_message_at', 'unread_count'
        ]
    
    def get_other_user_name(self, obj):
        request = self.context.get('request')
        if request and request.user:
            if request.user == obj.shopkeeper:
                return obj.buyer.full_name
            else:
                return obj.shopkeeper.full_name
        return None
    
    def get_other_user_image(self, obj):
        request = self.context.get('request')
        if request and request.user:
            if request.user == obj.shopkeeper:
                return obj.buyer.profile_image.url if obj.buyer.profile_image else None
            else:
                return obj.shopkeeper.profile_image.url if obj.shopkeeper.profile_image else None
        return None
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.get_unread_count(request.user)
        return 0
