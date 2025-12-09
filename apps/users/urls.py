"""
User URLs - Authentication endpoints
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    RegisterShopkeeperView,
    RegisterBuyerView,
    LoginView,
    LogoutView,
    ProfileView,
    ChangePasswordView,
    UpdateFCMTokenView,
    UpdateExpoPushTokenView,
    ShopkeeperProfileUpdateView,
    NotificationSettingsView,
    SupportTicketListCreateView,
    SupportTicketDetailView,
)

urlpatterns = [
    # Registration
    path('register-shopkeeper/', RegisterShopkeeperView.as_view(), name='register-shopkeeper'),
    path('register-buyer/', RegisterBuyerView.as_view(), name='register-buyer'),
    
    # Authentication
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    
    # Profile
    path('profile/', ProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('fcm-token/', UpdateFCMTokenView.as_view(), name='fcm-token'),
    path('expo-push-token/', UpdateExpoPushTokenView.as_view(), name='expo-push-token'),
    path('shopkeeper-profile/', ShopkeeperProfileUpdateView.as_view(), name='shopkeeper-profile'),
    path('notification-settings/', NotificationSettingsView.as_view(), name='notification-settings'),
    
    # Support Tickets
    path('support-tickets/', SupportTicketListCreateView.as_view(), name='support-tickets'),
    path('support-tickets/<uuid:pk>/', SupportTicketDetailView.as_view(), name='support-ticket-detail'),
]
