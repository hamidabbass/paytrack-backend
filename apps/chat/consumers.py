"""
WebSocket Consumer for Real-time Chat
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from .models import Conversation, Message
from .serializers import MessageSerializer


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for handling real-time chat messages.
    """
    
    async def connect(self):
        """Handle WebSocket connection."""
        self.user = self.scope['user']
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        
        # Reject connection if user is not authenticated
        if isinstance(self.user, AnonymousUser):
            await self.close()
            return
        
        # Verify user is part of the conversation
        is_participant = await self.is_conversation_participant()
        if not is_participant:
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to chat'
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'chat_message')
            
            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'typing':
                await self.handle_typing(data)
            elif message_type == 'read_receipt':
                await self.handle_read_receipt(data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
    
    async def handle_chat_message(self, data):
        """Handle incoming chat message."""
        message_text = data.get('message_text', '')
        message_type = data.get('message_type', 'text')
        image_url = data.get('image_url')
        voice_url = data.get('voice_url')
        voice_duration = data.get('voice_duration')
        
        # Save message to database
        message = await self.save_message(
            message_text=message_text,
            message_type=message_type,
            image_url=image_url,
            voice_url=voice_url,
            voice_duration=voice_duration
        )
        
        if message:
            # Broadcast message to room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message
                }
            )
    
    async def handle_typing(self, data):
        """Handle typing indicator."""
        is_typing = data.get('is_typing', False)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': str(self.user.id),
                'user_name': self.user.full_name,
                'is_typing': is_typing
            }
        )
    
    async def handle_read_receipt(self, data):
        """Handle read receipt."""
        await self.mark_messages_read()
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'read_receipt',
                'user_id': str(self.user.id)
            }
        )
    
    # Event handlers for group messages
    async def chat_message(self, event):
        """Send chat message to WebSocket."""
        message = event['message']
        
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': message
        }))
    
    async def typing_indicator(self, event):
        """Send typing indicator to WebSocket."""
        # Don't send typing indicator to the sender
        if event['user_id'] != str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user_id': event['user_id'],
                'user_name': event['user_name'],
                'is_typing': event['is_typing']
            }))
    
    async def read_receipt(self, event):
        """Send read receipt to WebSocket."""
        if event['user_id'] != str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'read_receipt',
                'user_id': event['user_id']
            }))
    
    # Database operations
    @database_sync_to_async
    def is_conversation_participant(self):
        """Check if user is a participant in the conversation."""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            return conversation.shopkeeper == self.user or conversation.buyer == self.user
        except Conversation.DoesNotExist:
            return False
    
    @database_sync_to_async
    def save_message(self, message_text, message_type, image_url=None, voice_url=None, voice_duration=None):
        """Save message to database."""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            
            # Determine receiver
            receiver = conversation.buyer if self.user == conversation.shopkeeper else conversation.shopkeeper
            
            # Create message
            message = Message.objects.create(
                conversation=conversation,
                sender=self.user,
                receiver=receiver,
                message_type=message_type,
                message_text=message_text,
                voice_duration=voice_duration
            )
            
            # Return serialized message
            return MessageSerializer(message).data
        except Conversation.DoesNotExist:
            return None
    
    @database_sync_to_async
    def mark_messages_read(self):
        """Mark all messages as read."""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            conversation.mark_as_read(self.user)
        except Conversation.DoesNotExist:
            pass
