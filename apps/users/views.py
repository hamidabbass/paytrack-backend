"""
User Views - Authentication and User Management endpoints
"""

from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth import get_user_model

from .models import ShopkeeperProfile, BuyerProfile, SupportTicket
from .serializers import (
    UserSerializer,
    ShopkeeperProfileSerializer,
    BuyerProfileSerializer,
    ShopkeeperRegistrationSerializer,
    BuyerRegistrationSerializer,
    LoginSerializer,
    TokenResponseSerializer,
    ChangePasswordSerializer,
    UpdateProfileSerializer,
    FCMTokenSerializer,
    SupportTicketSerializer,
)
from apps.core.permissions import IsShopkeeper

User = get_user_model()


class RegisterShopkeeperView(generics.CreateAPIView):
    """
    Register a new Shopkeeper account.
    POST /api/auth/register-shopkeeper/
    """
    permission_classes = [AllowAny]
    serializer_class = ShopkeeperRegistrationSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        # Get profile
        profile = ShopkeeperProfileSerializer(user.shopkeeper_profile).data
        
        return Response({
            'success': True,
            'message': 'Shopkeeper registered successfully.',
            'data': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserSerializer(user).data,
                'profile': profile
            }
        }, status=status.HTTP_201_CREATED)


class RegisterBuyerView(generics.CreateAPIView):
    """
    Register a new Buyer (by Shopkeeper).
    POST /api/auth/register-buyer/
    """
    permission_classes = [IsAuthenticated, IsShopkeeper]
    serializer_class = BuyerRegistrationSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Get profile
        profile = BuyerProfileSerializer(user.buyer_profile).data
        
        return Response({
            'success': True,
            'message': 'Buyer registered successfully.',
            'data': {
                'user': UserSerializer(user).data,
                'profile': profile
            }
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """
    Login with email and password.
    POST /api/auth/login/
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        # Get profile based on user type
        profile = None
        if user.user_type == 'shopkeeper':
            profile_obj = getattr(user, 'shopkeeper_profile', None)
            if profile_obj:
                profile = ShopkeeperProfileSerializer(profile_obj).data
        elif user.user_type == 'buyer':
            profile_obj = getattr(user, 'buyer_profile', None)
            if profile_obj:
                profile = BuyerProfileSerializer(profile_obj).data
        
        return Response({
            'success': True,
            'message': 'Login successful.',
            'data': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserSerializer(user).data,
                'profile': profile
            }
        })


class LogoutView(APIView):
    """
    Logout by blacklisting the refresh token.
    POST /api/auth/logout/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            return Response({
                'success': True,
                'message': 'Logout successful.'
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    """
    Get or update current user profile.
    GET/PUT /api/auth/profile/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get profile based on user type
        profile = None
        if user.user_type == 'shopkeeper':
            profile_obj = getattr(user, 'shopkeeper_profile', None)
            if profile_obj:
                profile = ShopkeeperProfileSerializer(profile_obj).data
        elif user.user_type == 'buyer':
            profile_obj = getattr(user, 'buyer_profile', None)
            if profile_obj:
                profile = BuyerProfileSerializer(profile_obj).data
        
        return Response({
            'success': True,
            'data': {
                'user': UserSerializer(user).data,
                'profile': profile
            }
        })
    
    def put(self, request):
        user = request.user
        serializer = UpdateProfileSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'success': True,
            'message': 'Profile updated successfully.',
            'data': {
                'user': UserSerializer(user).data
            }
        })


class ChangePasswordView(APIView):
    """
    Change password for current user.
    POST /api/auth/change-password/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({
            'success': True,
            'message': 'Password changed successfully.'
        })


class UpdateFCMTokenView(APIView):
    """
    Update FCM token for push notifications.
    POST /api/auth/fcm-token/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = FCMTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        user.fcm_token = serializer.validated_data['fcm_token']
        user.save()
        
        return Response({
            'success': True,
            'message': 'FCM token updated successfully.'
        })


class UpdateExpoPushTokenView(APIView):
    """
    Update Expo Push Token for mobile app notifications.
    POST /api/auth/expo-push-token/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        expo_push_token = request.data.get('expo_push_token')
        
        if not expo_push_token:
            return Response({
                'success': False,
                'message': 'expo_push_token is required.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        user.expo_push_token = expo_push_token
        user.save()
        
        return Response({
            'success': True,
            'message': 'Expo push token updated successfully.'
        })


class ShopkeeperProfileUpdateView(APIView):
    """
    Update shopkeeper profile.
    PUT /api/auth/shopkeeper-profile/
    """
    permission_classes = [IsAuthenticated, IsShopkeeper]
    
    def put(self, request):
        user = request.user
        profile = getattr(user, 'shopkeeper_profile', None)
        
        if not profile:
            return Response({
                'success': False,
                'message': 'Shopkeeper profile not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = ShopkeeperProfileSerializer(
            profile,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'success': True,
            'message': 'Shopkeeper profile updated successfully.',
            'data': serializer.data
        })


class NotificationSettingsView(APIView):
    """
    Get or update notification settings for current user.
    GET/PUT /api/auth/notification-settings/
    """
    permission_classes = [IsAuthenticated]
    
    DEFAULT_SETTINGS = {
        'push_enabled': True,
        'email_enabled': True,
        'sms_enabled': False,
        'payment_reminders': True,
        'payment_received': True,
        'overdue_alerts': True,
        'new_messages': True,
        'marketing_updates': False,
        'weekly_reports': True,
        'sound_enabled': True,
        'vibration_enabled': True,
    }
    
    def get(self, request):
        user = request.user
        settings = user.notification_settings or self.DEFAULT_SETTINGS.copy()
        
        # Merge with defaults to ensure all keys exist
        for key, value in self.DEFAULT_SETTINGS.items():
            if key not in settings:
                settings[key] = value
        
        return Response({
            'success': True,
            'data': settings
        })
    
    def put(self, request):
        user = request.user
        current_settings = user.notification_settings or self.DEFAULT_SETTINGS.copy()
        
        # Update only provided fields
        for key in request.data:
            if key in self.DEFAULT_SETTINGS:
                current_settings[key] = request.data[key]
        
        user.notification_settings = current_settings
        user.save(update_fields=['notification_settings'])
        
        return Response({
            'success': True,
            'message': 'Notification settings updated successfully.',
            'data': current_settings
        })


class SupportTicketListCreateView(generics.ListCreateAPIView):
    """
    List user's support tickets or create a new one.
    GET/POST /api/auth/support-tickets/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SupportTicketSerializer
    
    def get_queryset(self):
        return SupportTicket.objects.filter(user=self.request.user)
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        return Response({
            'success': True,
            'message': 'Support ticket created successfully. We will respond within 24 hours.',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)


class SupportTicketDetailView(generics.RetrieveAPIView):
    """
    Get details of a specific support ticket.
    GET /api/auth/support-tickets/<id>/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SupportTicketSerializer
    
    def get_queryset(self):
        return SupportTicket.objects.filter(user=self.request.user)
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'success': True,
            'data': serializer.data
        })


class ForgotPasswordView(APIView):
    """
    Request password reset OTP.
    POST /api/auth/forgot-password/
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        from .serializers import ForgotPasswordSerializer
        from .models import PasswordResetOTP
        import random
        from datetime import timedelta
        from django.core.mail import send_mail
        from django.conf import settings
        
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        
        # Invalidate any existing OTPs for this email
        PasswordResetOTP.objects.filter(email=email, is_used=False).update(is_used=True)
        
        # Generate 6-digit OTP
        otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Create OTP record (valid for 10 minutes)
        otp_record = PasswordResetOTP.objects.create(
            email=email,
            otp=otp,
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        # Try to send email (won't fail if email sending fails)
        try:
            send_mail(
                subject='Password Reset OTP - PayTrack',
                message=f'Your OTP for password reset is: {otp}\n\nThis OTP is valid for 10 minutes.\n\nIf you did not request this, please ignore this email.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"Email sending failed: {e}")
        
        return Response({
            'success': True,
            'message': 'If an account exists with this email, you will receive an OTP shortly.',
            'otp': otp  # Remove this in production! Only for testing
        })


class VerifyOTPView(APIView):
    """
    Verify OTP for password reset.
    POST /api/auth/verify-otp/
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        from .serializers import VerifyOTPSerializer
        from .models import PasswordResetOTP
        
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']
        
        # Find valid OTP
        otp_record = PasswordResetOTP.objects.filter(
            email=email,
            otp=otp,
            is_used=False
        ).order_by('-created_at').first()
        
        if not otp_record:
            return Response({
                'success': False,
                'message': 'Invalid OTP.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if otp_record.is_expired:
            return Response({
                'success': False,
                'message': 'OTP has expired. Please request a new one.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': True,
            'message': 'OTP verified successfully.'
        })


class ResetPasswordView(APIView):
    """
    Reset password with OTP.
    POST /api/auth/reset-password/
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        from .serializers import ResetPasswordSerializer
        from .models import PasswordResetOTP
        
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']
        
        # Find valid OTP
        otp_record = PasswordResetOTP.objects.filter(
            email=email,
            otp=otp,
            is_used=False
        ).order_by('-created_at').first()
        
        if not otp_record:
            return Response({
                'success': False,
                'message': 'Invalid OTP.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if otp_record.is_expired:
            return Response({
                'success': False,
                'message': 'OTP has expired. Please request a new one.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Mark OTP as used
        otp_record.is_used = True
        otp_record.save()
        
        # Update user's password
        user = User.objects.get(email=email)
        user.set_password(new_password)
        user.save()
        
        return Response({
            'success': True,
            'message': 'Password reset successfully. You can now login with your new password.'
        })
