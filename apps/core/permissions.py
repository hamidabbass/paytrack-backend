"""
Custom Permissions for the application
"""

from rest_framework.permissions import BasePermission


class IsShopkeeper(BasePermission):
    """
    Permission class to check if user is a shopkeeper.
    """
    message = 'Only shopkeepers can perform this action.'
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.user_type == 'shopkeeper'
        )


class IsBuyer(BasePermission):
    """
    Permission class to check if user is a buyer.
    """
    message = 'Only buyers can perform this action.'
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.user_type == 'buyer'
        )


class IsOwnerOrShopkeeper(BasePermission):
    """
    Permission class to check if user is owner or the shopkeeper.
    """
    
    def has_object_permission(self, request, view, obj):
        # Check if user is the shopkeeper for this object
        if hasattr(obj, 'shopkeeper'):
            if obj.shopkeeper == request.user:
                return True
        
        # Check if user is the buyer for this object
        if hasattr(obj, 'buyer'):
            if obj.buyer == request.user:
                return True
        
        # Check if user is the owner
        if hasattr(obj, 'user'):
            if obj.user == request.user:
                return True
        
        return False


class IsConversationParticipant(BasePermission):
    """
    Permission class to check if user is a participant in the conversation.
    """
    message = 'You are not a participant in this conversation.'
    
    def has_object_permission(self, request, view, obj):
        return obj.shopkeeper == request.user or obj.buyer == request.user
