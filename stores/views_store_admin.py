"""
Store Admin API views - allows store owners to manage their own products.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from decimal import Decimal

from products.models import Product, Category, Subcategory, Brand, Currency, SKU, ProductImage, ProductFeature
from products.serializers import ProductDetailSerializer, ProductListSerializer
from .models import Store
from .permissions import IsStoreOwner, IsStoreOwnerOrReadOnly
from .serializers import StoreAdminProductSerializer
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from drf_spectacular.types import OpenApiTypes


@extend_schema(
    summary="List store's products",
    description="Get a list of all products for the authenticated store owner's stores",
    parameters=[
        OpenApiParameter('store_id', OpenApiTypes.INT, description='Filter by specific store ID', required=False),
        OpenApiParameter('search', OpenApiTypes.STR, description='Search products by name', required=False),
        OpenApiParameter('is_active', OpenApiTypes.BOOL, description='Filter by active status', required=False),
        OpenApiParameter('in_stock', OpenApiTypes.BOOL, description='Filter by stock status', required=False),
    ],
    responses={
        200: ProductListSerializer(many=True),
        403: OpenApiResponse(description="Not a store owner"),
    },
    tags=["store-admin"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsStoreOwner])
def store_admin_product_list(request):
    """
    List all products for stores owned by the authenticated user.
    """
    user = request.user
    
    # Get all stores owned by user (or all stores if superuser)
    if user.is_superuser:
        stores = Store.objects.filter(is_active=True)
    else:
        stores = Store.objects.filter(owner=user, is_active=True)
    
    # Filter by specific store if provided
    store_id = request.query_params.get('store_id')
    if store_id:
        stores = stores.filter(id=store_id)
        if not stores.exists():
            return Response(
                {'error': 'Store not found or you do not have permission'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    # Get products from user's stores
    products = Product.objects.filter(store__in=stores).select_related(
        'category', 'subcategory', 'second_subcategory', 'brand', 'store', 'currency'
    ).prefetch_related('images', 'skus', 'features')
    
    # Apply filters
    search = request.query_params.get('search')
    if search:
        products = products.filter(name__icontains=search)
    
    is_active = request.query_params.get('is_active')
    if is_active is not None:
        products = products.filter(is_active=is_active.lower() == 'true')
    
    in_stock = request.query_params.get('in_stock')
    if in_stock is not None:
        products = products.filter(in_stock=in_stock.lower() == 'true')
    
    # Order by creation date
    products = products.order_by('-created_at')
    
    serializer = ProductListSerializer(products, many=True, context={'request': request})
    return Response({
        'success': True,
        'products': serializer.data,
        'total': products.count(),
    }, status=status.HTTP_200_OK)


@extend_schema(
    summary="Get store's product detail",
    description="Get detailed information about a specific product from store owner's stores",
    responses={
        200: ProductDetailSerializer,
        403: OpenApiResponse(description="Not store owner or product not found"),
        404: OpenApiResponse(description="Product not found"),
    },
    tags=["store-admin"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsStoreOwner])
def store_admin_product_detail(request, product_id):
    """
    Get detailed information about a specific product.
    Only accessible if product belongs to user's store.
    """
    try:
        product = Product.objects.select_related(
            'category', 'subcategory', 'second_subcategory', 'brand', 'store', 'currency'
        ).prefetch_related('images', 'skus', 'features').get(id=product_id)
    except Product.DoesNotExist:
        return Response(
            {'error': 'Product not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if user owns the store
    if product.store.owner != request.user and not request.user.is_superuser:
        return Response(
            {'error': 'You do not have permission to access this product'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = ProductDetailSerializer(product, context={'request': request})
    return Response({
        'success': True,
        'product': serializer.data,
    }, status=status.HTTP_200_OK)


@extend_schema(
    summary="Create product",
    description="Create a new product for store owner's store",
    request=ProductDetailSerializer,
    responses={
        201: ProductDetailSerializer,
        400: OpenApiResponse(description="Validation error"),
        403: OpenApiResponse(description="Not a store owner"),
    },
    tags=["store-admin"],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsStoreOwner])
def store_admin_product_create(request):
    """
    Create a new product for store owner's store.
    """
    # Get store_id from request data
    store_id = request.data.get('store')
    if not store_id:
        return Response(
            {'error': 'store field is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verify user owns the store
    try:
        store = Store.objects.get(id=store_id, owner=request.user, is_active=True)
    except Store.DoesNotExist:
        return Response(
            {'error': 'Store not found or you do not have permission'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Use StoreAdminProductSerializer for creation
    serializer = StoreAdminProductSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        # Ensure store is set correctly
        product = serializer.save(store=store)
        return Response({
            'success': True,
            'product': ProductDetailSerializer(product, context={'request': request}).data,
        }, status=status.HTTP_201_CREATED)
    
    return Response({
        'success': False,
        'errors': serializer.errors,
    }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Update product",
    description="Update an existing product from store owner's store",
    request=ProductDetailSerializer,
    responses={
        200: ProductDetailSerializer,
        400: OpenApiResponse(description="Validation error"),
        403: OpenApiResponse(description="Not store owner"),
        404: OpenApiResponse(description="Product not found"),
    },
    tags=["store-admin"],
)
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated, IsStoreOwner])
def store_admin_product_update(request, product_id):
    """
    Update an existing product.
    Only accessible if product belongs to user's store.
    """
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response(
            {'error': 'Product not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if user owns the store
    if product.store.owner != request.user and not request.user.is_superuser:
        return Response(
            {'error': 'You do not have permission to update this product'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Prevent changing store ownership
    if 'store' in request.data:
        new_store_id = request.data['store']
        if new_store_id != product.store.id:
            return Response(
                {'error': 'Cannot change product store ownership'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Use StoreAdminProductSerializer for updates
    serializer = StoreAdminProductSerializer(product, data=request.data, partial=True, context={'request': request})
    
    if serializer.is_valid():
        updated_product = serializer.save()
        # Refresh from database to get latest data
        updated_product.refresh_from_db()
        return Response({
            'success': True,
            'product': ProductDetailSerializer(updated_product, context={'request': request}).data,
        }, status=status.HTTP_200_OK)
    
    return Response({
        'success': False,
        'errors': serializer.errors,
    }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Delete product",
    description="Delete a product from store owner's store",
    responses={
        200: OpenApiResponse(description="Product deleted successfully"),
        403: OpenApiResponse(description="Not store owner"),
        404: OpenApiResponse(description="Product not found"),
    },
    tags=["store-admin"],
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsStoreOwner])
def store_admin_product_delete(request, product_id):
    """
    Delete a product.
    Only accessible if product belongs to user's store.
    """
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response(
            {'error': 'Product not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if user owns the store
    if product.store.owner != request.user and not request.user.is_superuser:
        return Response(
            {'error': 'You do not have permission to delete this product'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    product.delete()
    
    return Response({
        'success': True,
        'message': 'Product deleted successfully',
    }, status=status.HTTP_200_OK)


@extend_schema(
    summary="Get store owner's stores",
    description="Get list of stores owned by authenticated user",
    responses={
        200: OpenApiResponse(description="List of stores"),
    },
    tags=["store-admin"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsStoreOwner])
def store_admin_my_stores(request):
    """
    Get list of stores owned by authenticated user.
    """
    stores = Store.objects.filter(owner=request.user, is_active=True)
    
    stores_data = []
    for store in stores:
        stores_data.append({
            'id': store.id,
            'name': store.name,
            'slug': store.slug,
            'market': store.market,
            'status': store.status,
            'is_verified': store.is_verified,
            'products_count': store.products.filter(is_active=True).count(),
        })
    
    return Response({
        'success': True,
        'stores': stores_data,
        'total': stores.count(),
    }, status=status.HTTP_200_OK)

