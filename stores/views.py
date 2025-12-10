"""
Views for Stores app - Multi-store marketplace.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404

from .models import Store, StoreFollower
from .serializers import StoreListSerializer, StoreDetailSerializer
from products.models import Product
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from drf_spectacular.types import OpenApiTypes


MARKET_PARAM = OpenApiParameter(
    name='market',
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    description='Market filter (KG or US)',
    required=False,
    enum=['KG', 'US']
)

LIMIT_PARAM = OpenApiParameter(
    name='limit',
    type=OpenApiTypes.INT,
    location=OpenApiParameter.QUERY,
    description='Number of results per page',
    required=False
)

OFFSET_PARAM = OpenApiParameter(
    name='offset',
    type=OpenApiTypes.INT,
    location=OpenApiParameter.QUERY,
    description='Number of results to skip',
    required=False
)


def resolve_market(request):
    """Resolve market from request (user location, header, or query param)."""
    # Priority: authenticated user → X-Market header → query param → default
    if request.user and request.user.is_authenticated:
        market = getattr(request.user, 'location', None)
        if market:
            return market
    
    header_market = request.headers.get('X-Market')
    if header_market:
        return header_market.upper()
    
    query_market = request.query_params.get('market')
    if query_market:
        return query_market.upper()
    
    return 'KG'  # Default


@extend_schema(
    summary="List stores",
    description="Get list of active stores with filtering and pagination",
    parameters=[MARKET_PARAM, LIMIT_PARAM, OFFSET_PARAM],
    responses={
        200: StoreListSerializer(many=True),
    },
    tags=["stores"],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def store_list(request):
    """
    Get list of active stores.
    
    Filters:
    - market: Market filter (KG or US)
    - limit: Number of results per page (default: 20)
    - offset: Number of results to skip (default: 0)
    """
    market = resolve_market(request)
    if market not in ['KG', 'US']:
        market = 'KG'
    
    limit = int(request.query_params.get('limit', 20))
    offset = int(request.query_params.get('offset', 0))
    
    # Base queryset - active stores
    queryset = Store.objects.filter(
        is_active=True,
        status='active'
    ).filter(
        Q(market=market) | Q(market='ALL')
    ).order_by('-is_featured', '-rating', '-created_at')
    
    # Get total count
    total = queryset.count()
    
    # Apply pagination
    stores = queryset[offset:offset + limit]
    
    # Serialize
    serializer = StoreListSerializer(stores, many=True, context={'request': request})
    
    return Response({
        'success': True,
        'stores': serializer.data,
        'total': total,
        'limit': limit,
        'offset': offset,
        'has_more': (offset + limit) < total,
    }, status=status.HTTP_200_OK)


@extend_schema(
    summary="Get store detail",
    description="Get detailed information about a specific store",
    responses={
        200: StoreDetailSerializer,
        404: OpenApiResponse(description="Store not found"),
    },
    tags=["stores"],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def store_detail(request, store_slug):
    """
    Get detailed information about a specific store by slug.
    """
    store = get_object_or_404(Store, slug=store_slug, is_active=True)
    
    serializer = StoreDetailSerializer(store, context={'request': request})
    
    return Response({
        'success': True,
        'store': serializer.data,
    }, status=status.HTTP_200_OK)


@extend_schema(
    summary="Get store products",
    description="Get products from a specific store",
    parameters=[MARKET_PARAM, LIMIT_PARAM, OFFSET_PARAM],
    responses={
        200: OpenApiResponse(description="List of products"),
        404: OpenApiResponse(description="Store not found"),
    },
    tags=["stores"],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def store_products(request, store_slug):
    """
    Get products from a specific store.
    
    Filters:
    - market: Market filter (KG or US)
    - limit: Number of results per page (default: 20)
    - offset: Number of results to skip (default: 0)
    """
    store = get_object_or_404(Store, slug=store_slug, is_active=True)
    
    market = resolve_market(request)
    if market not in ['KG', 'US']:
        market = 'KG'
    
    limit = int(request.query_params.get('limit', 20))
    offset = int(request.query_params.get('offset', 0))
    
    # Get products from this store
    queryset = Product.objects.filter(
        store=store,
        is_active=True,
        in_stock=True
    ).filter(
        Q(market=market) | Q(market='ALL')
    ).order_by('-is_featured', '-sales_count', '-rating', '-created_at')
    
    # Get total count
    total = queryset.count()
    
    # Apply pagination
    products = queryset[offset:offset + limit]
    
    # Use product list serializer (we'll need to import it)
    from products.serializers import ProductListSerializer
    serializer = ProductListSerializer(products, many=True, context={'request': request})
    
    return Response({
        'success': True,
        'store': {
            'id': store.id,
            'name': store.name,
            'slug': store.slug,
        },
        'products': serializer.data,
        'total': total,
        'limit': limit,
        'offset': offset,
        'has_more': (offset + limit) < total,
    }, status=status.HTTP_200_OK)


@extend_schema(
    summary="Follow/Unfollow store",
    description="Toggle follow status for a store",
    responses={
        200: OpenApiResponse(description="Follow status updated"),
        404: OpenApiResponse(description="Store not found"),
    },
    tags=["stores"],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_follow_store(request, store_slug):
    """
    Follow or unfollow a store.
    """
    store = get_object_or_404(Store, slug=store_slug, is_active=True)
    user = request.user
    
    # Check if already following
    follower, created = StoreFollower.objects.get_or_create(
        user=user,
        store=store
    )
    
    if not created:
        # Already following, so unfollow
        follower.delete()
        is_following = False
        message = 'Store unfollowed successfully'
    else:
        # Now following
        is_following = True
        message = 'Store followed successfully'
    
    # Update store likes count
    store.likes_count = store.followers.count()
    store.save(update_fields=['likes_count'])
    
    return Response({
        'success': True,
        'message': message,
        'is_following': is_following,
        'likes_count': store.likes_count,
    }, status=status.HTTP_200_OK)


@extend_schema(
    summary="Get store statistics",
    description="Get statistics for a store (for store owner dashboard)",
    responses={
        200: OpenApiResponse(description="Store statistics"),
        403: OpenApiResponse(description="Not store owner"),
        404: OpenApiResponse(description="Store not found"),
    },
    tags=["stores"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def store_statistics(request, store_slug):
    """
    Get statistics for a store (only accessible by store owner).
    """
    store = get_object_or_404(Store, slug=store_slug)
    
    # Check if user is the store owner
    if store.owner != request.user:
        return Response(
            {'error': 'You are not the owner of this store'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Update statistics
    store.update_statistics()
    
    return Response({
        'success': True,
        'statistics': {
            'rating': float(store.rating),
            'reviews_count': store.reviews_count,
            'orders_count': store.orders_count,
            'products_count': store.products_count,
            'likes_count': store.likes_count,
        },
    }, status=status.HTTP_200_OK)
