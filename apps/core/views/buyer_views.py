"""
Core Views - Buyer management endpoints
"""

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Sum, Count, Q
from django.contrib.auth import get_user_model

from apps.users.models import User, BuyerProfile
from apps.users.serializers import UserSerializer, BuyerProfileSerializer
from apps.core.permissions import IsShopkeeper
from apps.core.models import InstallmentPlan

User = get_user_model()


class BuyerListCreateView(generics.ListCreateAPIView):
    """
    List all buyers or create a new buyer for the current shopkeeper.
    GET /api/buyers/
    POST /api/buyers/
    """
    permission_classes = [IsAuthenticated, IsShopkeeper]
    serializer_class = BuyerProfileSerializer
    
    def get_queryset(self):
        return BuyerProfile.objects.filter(
            shopkeeper=self.request.user
        ).select_related('user').order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'success': True,
            'count': queryset.count(),
            'data': serializer.data
        })
    
    def create(self, request, *args, **kwargs):
        """Create a new buyer for this shopkeeper."""
        data = request.data
        
        # Create user for the buyer
        email = data.get('email', '')
        phone = data.get('phone', '')
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        
        # Generate a random password or use provided one
        import secrets
        password = data.get('password', secrets.token_urlsafe(12))
        
        # Check if email already exists (if provided)
        if email and User.objects.filter(email=email).exists():
            return Response({
                'success': False,
                'message': 'A user with this email already exists.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # If no email provided, generate one based on phone
        if not email and phone:
            email = f"{phone.replace('+', '').replace(' ', '').replace('-', '')}@buyer.local"
        elif not email:
            email = f"buyer_{secrets.token_hex(4)}@buyer.local"
        
        try:
            # Create user
            user = User.objects.create_user(
                email=email,
                phone=phone,
                first_name=first_name,
                last_name=last_name,
                password=password,
                user_type='buyer'
            )
            
            # Create buyer profile
            buyer_profile = BuyerProfile.objects.create(
                user=user,
                shopkeeper=request.user,
                cnic_number=data.get('cnic_number', ''),
                occupation=data.get('occupation', ''),
                monthly_income=data.get('monthly_income'),
                reference_name=data.get('reference_name', ''),
                reference_phone=data.get('reference_phone', '')
            )
            
            serializer = self.get_serializer(buyer_profile)
            
            return Response({
                'success': True,
                'message': 'Buyer created successfully.',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class BuyerDetailView(generics.RetrieveUpdateAPIView):
    """
    Get or update a specific buyer.
    GET/PUT /api/buyers/{id}/
    """
    permission_classes = [IsAuthenticated, IsShopkeeper]
    serializer_class = BuyerProfileSerializer
    lookup_field = 'user__id'
    lookup_url_kwarg = 'id'
    
    def get_queryset(self):
        return BuyerProfile.objects.filter(
            shopkeeper=self.request.user
        ).select_related('user')
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        # Get installment summary for this buyer
        installment_summary = InstallmentPlan.objects.filter(
            buyer=instance.user,
            shopkeeper=request.user
        ).aggregate(
            total_plans=Count('id'),
            active_plans=Count('id', filter=Q(status='active')),
            total_amount=Sum('total_amount'),
            total_remaining=Sum('remaining_amount')
        )
        
        data = serializer.data
        data['installment_summary'] = {
            'total_plans': installment_summary['total_plans'] or 0,
            'active_plans': installment_summary['active_plans'] or 0,
            'total_amount': str(installment_summary['total_amount'] or 0),
            'total_remaining': str(installment_summary['total_remaining'] or 0)
        }
        
        return Response({
            'success': True,
            'data': data
        })


class BuyerSearchView(APIView):
    """
    Search buyers by name, phone, or CNIC.
    GET /api/buyers/search/?q=search_term
    """
    permission_classes = [IsAuthenticated, IsShopkeeper]
    
    def get(self, request):
        query = request.query_params.get('q', '').strip()
        
        if not query:
            return Response({
                'success': False,
                'message': 'Search query is required.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        buyers = BuyerProfile.objects.filter(
            shopkeeper=request.user
        ).filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__phone__icontains=query) |
            Q(cnic_number__icontains=query)
        ).select_related('user')[:20]
        
        serializer = BuyerProfileSerializer(buyers, many=True)
        
        return Response({
            'success': True,
            'count': len(serializer.data),
            'data': serializer.data
        })


class BuyerStatsView(APIView):
    """
    Get statistics for all buyers.
    GET /api/buyers/stats/
    """
    permission_classes = [IsAuthenticated, IsShopkeeper]
    
    def get(self, request):
        total_buyers = BuyerProfile.objects.filter(
            shopkeeper=request.user
        ).count()
        
        active_buyers = BuyerProfile.objects.filter(
            shopkeeper=request.user,
            user__installment_plans__status='active'
        ).distinct().count()
        
        blacklisted_buyers = BuyerProfile.objects.filter(
            shopkeeper=request.user,
            is_blacklisted=True
        ).count()
        
        return Response({
            'success': True,
            'data': {
                'total_buyers': total_buyers,
                'active_buyers': active_buyers,
                'blacklisted_buyers': blacklisted_buyers
            }
        })


class BuyerBlacklistView(APIView):
    """
    Blacklist or unblacklist a buyer.
    POST /api/buyers/{id}/blacklist/
    """
    permission_classes = [IsAuthenticated, IsShopkeeper]
    
    def post(self, request, id):
        try:
            buyer_profile = BuyerProfile.objects.get(
                user__id=id,
                shopkeeper=request.user
            )
        except BuyerProfile.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Buyer not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        action = request.data.get('action', 'blacklist')
        reason = request.data.get('reason', '')
        
        if action == 'blacklist':
            buyer_profile.is_blacklisted = True
            buyer_profile.blacklist_reason = reason
            message = 'Buyer has been blacklisted.'
        else:
            buyer_profile.is_blacklisted = False
            buyer_profile.blacklist_reason = None
            message = 'Buyer has been removed from blacklist.'
        
        buyer_profile.save()
        
        return Response({
            'success': True,
            'message': message,
            'data': BuyerProfileSerializer(buyer_profile).data
        })
