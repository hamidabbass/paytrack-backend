"""
Core Views - Product management endpoints
"""

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsShopkeeper
from apps.core.models import Product
from apps.core.serializers import ProductSerializer, ProductListSerializer


class ProductListView(generics.ListCreateAPIView):
    """
    List all products or create a new product.
    GET/POST /api/products/
    """
    permission_classes = [IsAuthenticated, IsShopkeeper]
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ProductListSerializer
        return ProductSerializer
    
    def get_queryset(self):
        queryset = Product.objects.filter(shopkeeper=self.request.user)
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Search by name
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        return queryset.order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'success': True,
            'count': queryset.count(),
            'data': serializer.data
        })
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        
        return Response({
            'success': True,
            'message': 'Product created successfully.',
            'data': ProductSerializer(product).data
        }, status=status.HTTP_201_CREATED)


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Get, update, or delete a product.
    GET/PUT/DELETE /api/products/{id}/
    """
    permission_classes = [IsAuthenticated, IsShopkeeper]
    serializer_class = ProductSerializer
    lookup_field = 'id'
    
    def get_queryset(self):
        return Product.objects.filter(shopkeeper=self.request.user)
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        
        return Response({
            'success': True,
            'message': 'Product updated successfully.',
            'data': ProductSerializer(product).data
        })
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        
        return Response({
            'success': True,
            'message': 'Product deleted successfully.'
        }, status=status.HTTP_200_OK)


class ProductCategoriesView(APIView):
    """
    Get all product categories.
    GET /api/products/categories/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        categories = [
            {'value': choice[0], 'label': choice[1]}
            for choice in Product.CATEGORY_CHOICES
        ]
        
        return Response({
            'success': True,
            'data': categories
        })
