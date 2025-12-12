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
from .serializers import (
    StoreListSerializer,
    StoreDetailSerializer,
    StoreRegistrationSerializer,
    StoreUpdateSerializer,
)
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
    Get products from a specific store with filtering support.
    
    Filters:
    - market: Market filter (KG or US)
    - category: Category slug
    - subcategory: Subcategory slug
    - sizes: Comma-separated list of sizes
    - colors: Comma-separated list of colors
    - brands: Comma-separated list of brand slugs/names
    - price_min: Minimum price
    - price_max: Maximum price
    - sort_by: Sort order (popular, price_asc, price_desc, newest, rating)
    - limit: Number of results per page (default: 20)
    - offset: Number of results to skip (default: 0)
    """
    store = get_object_or_404(Store, slug=store_slug, is_active=True)
    
    market = resolve_market(request)
    if market not in ['KG', 'US']:
        market = 'KG'
    
    limit = int(request.query_params.get('limit', 20))
    offset = int(request.query_params.get('offset', 0))
    
    # Base queryset - products from this store
    queryset = Product.objects.filter(
        store=store,
        is_active=True,
        in_stock=True
    ).filter(
        Q(market=market) | Q(market='ALL')
    )
    
    # Apply filters
    # Category filter
    if category_slug := request.query_params.get('category'):
        queryset = queryset.filter(category__slug=category_slug)
    
    # Subcategory filter
    if subcategory_slug := request.query_params.get('subcategory'):
        queryset = queryset.filter(subcategory__slug=subcategory_slug)
    
    # Size filter
    if sizes := request.query_params.get('sizes'):
        size_list = [size.strip() for size in sizes.split(',') if size.strip()]
        queryset = queryset.filter(
            skus__size_option__name__in=size_list
        )
    
    # Color filter
    if colors := request.query_params.get('colors'):
        color_list = [color.strip() for color in colors.split(',') if color.strip()]
        queryset = queryset.filter(
            skus__color_option__name__in=color_list
        )
    
    # Brand filter
    if brands := request.query_params.get('brands'):
        brand_list = [brand.strip() for brand in brands.split(',') if brand.strip()]
        queryset = queryset.filter(
            Q(brand__slug__in=brand_list) | Q(brand__name__in=brand_list)
        )
    
    # Price filters
    if price_min := request.query_params.get('price_min'):
        try:
            queryset = queryset.filter(skus__price__gte=float(price_min))
        except ValueError:
            pass
    
    if price_max := request.query_params.get('price_max'):
        try:
            queryset = queryset.filter(skus__price__lte=float(price_max))
        except ValueError:
            pass
    
    # Apply sorting
    sort_by = request.query_params.get('sort_by', 'popular')
    if sort_by == 'price_asc':
        queryset = queryset.order_by('skus__price')
    elif sort_by == 'price_desc':
        queryset = queryset.order_by('-skus__price')
    elif sort_by == 'newest':
        queryset = queryset.order_by('-created_at')
    elif sort_by == 'rating':
        queryset = queryset.order_by('-rating', '-reviews_count')
    else:  # popular (default)
        queryset = queryset.order_by('-is_featured', '-sales_count', '-rating', '-created_at')
    
    # Get distinct products (in case of multiple SKUs matching filters)
    queryset = queryset.distinct()
    
    # Get available filters for this store's products (before applying user filters)
    base_queryset = Product.objects.filter(
        store=store,
        is_active=True,
        in_stock=True
    ).filter(
        Q(market=market) | Q(market='ALL')
    )
    
    # Get available filters using the same method as SubcategoryProductsView
    from products.views import SubcategoryProductsView
    from products.models import Category, Subcategory
    from django.db.models import Min, Max
    
    available_filters = SubcategoryProductsView._get_available_filters(base_queryset)
    
    # Add categories and subcategories to filters
    category_ids = base_queryset.values_list('category__id', flat=True).distinct().exclude(category__isnull=True)
    categories = Category.objects.filter(id__in=category_ids, is_active=True).order_by('name')
    available_filters['categories'] = [
        {'id': cat.id, 'name': cat.name, 'slug': cat.slug}
        for cat in categories
    ]
    
    subcategory_ids = base_queryset.values_list('subcategory__id', flat=True).distinct().exclude(subcategory__isnull=True)
    subcategories = Subcategory.objects.filter(id__in=subcategory_ids, is_active=True).order_by('name')
    available_filters['subcategories'] = [
        {'id': subcat.id, 'name': subcat.name, 'slug': subcat.slug}
        for subcat in subcategories
    ]
    
    # Get total count
    total = queryset.count()
    
    # Apply pagination
    products = queryset[offset:offset + limit]
    
    # Use product list serializer
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
        'filters': available_filters,
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


@extend_schema(
    summary="Register new store",
    description="Register a new store (requires authentication). Store will be in 'pending' status until admin approval.",
    request=StoreRegistrationSerializer,
    responses={
        201: StoreDetailSerializer,
        400: OpenApiResponse(description="Validation error"),
    },
    tags=["stores"],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def store_register(request):
    """
    Register a new store.
    
    The authenticated user becomes the store owner.
    Store status will be 'pending' until admin approval.
    """
    serializer = StoreRegistrationSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        store = serializer.save()
        response_serializer = StoreDetailSerializer(store, context={'request': request})
        return Response({
            'success': True,
            'message': 'Store registered successfully. Pending admin approval.',
            'store': response_serializer.data,
        }, status=status.HTTP_201_CREATED)
    
    return Response({
        'success': False,
        'errors': serializer.errors,
    }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Update store",
    description="Update store information (store owner only)",
    request=StoreUpdateSerializer,
    responses={
        200: StoreDetailSerializer,
        400: OpenApiResponse(description="Validation error"),
        403: OpenApiResponse(description="Not store owner"),
        404: OpenApiResponse(description="Store not found"),
    },
    tags=["stores"],
)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def store_update(request, store_slug):
    """
    Update store information (store owner only).
    """
    store = get_object_or_404(Store, slug=store_slug)
    
    # Check if user is the store owner
    if store.owner != request.user:
        return Response(
            {'error': 'You are not the owner of this store'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = StoreUpdateSerializer(store, data=request.data, partial=True, context={'request': request})
    
    if serializer.is_valid():
        serializer.save()
        response_serializer = StoreDetailSerializer(store, context={'request': request})
        return Response({
            'success': True,
            'message': 'Store updated successfully',
            'store': response_serializer.data,
        }, status=status.HTTP_200_OK)
    
    return Response({
        'success': False,
        'errors': serializer.errors,
    }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Get my stores",
    description="Get list of stores owned by the authenticated user",
    responses={
        200: StoreListSerializer(many=True),
    },
    tags=["stores"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_stores(request):
    """
    Get list of stores owned by the authenticated user.
    """
    stores = Store.objects.filter(owner=request.user).order_by('-created_at')
    
    serializer = StoreListSerializer(stores, many=True, context={'request': request})
    
    return Response({
        'success': True,
        'stores': serializer.data,
        'total': stores.count(),
    }, status=status.HTTP_200_OK)
