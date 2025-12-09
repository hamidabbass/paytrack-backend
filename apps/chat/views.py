"""
Chat Views - Conversation and Message endpoints
"""

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q

from .models import Conversation, Message
from .serializers import (
    ConversationSerializer,
    ConversationListSerializer,
    ConversationCreateSerializer,
    MessageSerializer,
    MessageCreateSerializer,
)
from apps.core.permissions import IsConversationParticipant


class ConversationListView(generics.ListAPIView):
    """
    List all conversations for the current user.
    GET /api/chat/conversations/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ConversationListSerializer
    
    def get_queryset(self):
        user = self.request.user
        return Conversation.objects.filter(
            Q(shopkeeper=user) | Q(buyer=user)
        ).select_related('shopkeeper', 'buyer', 'last_message_sender')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'success': True,
            'count': queryset.count(),
            'data': serializer.data
        })


class ConversationCreateView(APIView):
    """
    Create or get an existing conversation.
    POST /api/chat/create/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Only shopkeepers can create conversations
        if request.user.user_type != 'shopkeeper':
            return Response({
                'success': False,
                'message': 'Only shopkeepers can create conversations.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = ConversationCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        buyer_id = serializer.validated_data['buyer_id']
        
        # Get or create conversation
        from apps.users.models import User
        buyer = User.objects.get(id=buyer_id)
        
        conversation, created = Conversation.objects.get_or_create(
            shopkeeper=request.user,
            buyer=buyer
        )
        
        return Response({
            'success': True,
            'message': 'Conversation created.' if created else 'Conversation retrieved.',
            'data': ConversationSerializer(conversation, context={'request': request}).data
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class ConversationDetailView(generics.RetrieveAPIView):
    """
    Get a specific conversation.
    GET /api/chat/conversations/{id}/
    """
    permission_classes = [IsAuthenticated, IsConversationParticipant]
    serializer_class = ConversationSerializer
    lookup_field = 'id'
    
    def get_queryset(self):
        user = self.request.user
        return Conversation.objects.filter(
            Q(shopkeeper=user) | Q(buyer=user)
        )
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Mark messages as read
        instance.mark_as_read(request.user)
        
        serializer = self.get_serializer(instance)
        
        return Response({
            'success': True,
            'data': serializer.data
        })


class MessageListView(generics.ListAPIView):
    """
    List messages in a conversation.
    GET /api/chat/messages/{conversation_id}/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer
    
    def get_queryset(self):
        conversation_id = self.kwargs.get('conversation_id')
        user = self.request.user
        
        # Verify user is part of the conversation
        try:
            conversation = Conversation.objects.get(
                Q(shopkeeper=user) | Q(buyer=user),
                id=conversation_id
            )
        except Conversation.DoesNotExist:
            return Message.objects.none()
        
        # Mark messages as read
        conversation.mark_as_read(user)
        
        return Message.objects.filter(
            conversation=conversation,
            is_deleted=False
        ).select_related('sender', 'receiver').order_by('created_at')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'success': True,
            'count': queryset.count(),
            'data': serializer.data
        })


class MessageSendView(APIView):
    """
    Send a message in a conversation.
    POST /api/chat/send/{conversation_id}/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, conversation_id):
        user = request.user
        
        # Get conversation
        try:
            conversation = Conversation.objects.get(
                Q(shopkeeper=user) | Q(buyer=user),
                id=conversation_id
            )
        except Conversation.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Conversation not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Determine receiver
        receiver = conversation.buyer if user == conversation.shopkeeper else conversation.shopkeeper
        
        # Create message
        message = Message.objects.create(
            conversation=conversation,
            sender=user,
            receiver=receiver,
            **serializer.validated_data
        )
        
        return Response({
            'success': True,
            'message': 'Message sent successfully.',
            'data': MessageSerializer(message).data
        }, status=status.HTTP_201_CREATED)


class MessageMarkReadView(APIView):
    """
    Mark messages as read.
    POST /api/chat/messages/read/{conversation_id}/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, conversation_id):
        user = request.user
        
        try:
            conversation = Conversation.objects.get(
                Q(shopkeeper=user) | Q(buyer=user),
                id=conversation_id
            )
        except Conversation.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Conversation not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        conversation.mark_as_read(user)
        
        return Response({
            'success': True,
            'message': 'Messages marked as read.'
        })


class UnreadCountView(APIView):
    """
    Get total unread message count.
    GET /api/chat/unread-count/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        if user.user_type == 'shopkeeper':
            total_unread = Conversation.objects.filter(
                shopkeeper=user
            ).aggregate(
                total=models.Sum('shopkeeper_unread_count')
            )['total'] or 0
        else:
            total_unread = Conversation.objects.filter(
                buyer=user
            ).aggregate(
                total=models.Sum('buyer_unread_count')
            )['total'] or 0
        
        return Response({
            'success': True,
            'data': {
                'unread_count': total_unread
            }
        })


# Import models for aggregate
from django.db import models
