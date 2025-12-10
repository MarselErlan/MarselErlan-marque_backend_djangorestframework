"""
Views for Store Manager App
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal

from orders.models import Order, OrderItem
from .models import StoreManager, ManagerSettings, RevenueSnapshot
from .serializers import (
    ManagerOrderListSerializer, ManagerOrderDetailSerializer,
    OrderStatusUpdateSerializer, DashboardStatsSerializer,
    RevenueAnalyticsSerializer, SuccessMessageSerializer,
    ManagerStatusSerializer
)
from .utils import (
    get_active_orders_count, get_today_orders, get_today_revenue,
    get_hourly_revenue, get_recent_orders, filter_orders_by_status,
    log_manager_activity, create_or_update_revenue_snapshot
)
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from drf_spectacular.types import OpenApiTypes


# Helper function to get manager from user
def get_manager(request):
    """Get StoreManager instance from request user"""
    try:
        return StoreManager.objects.select_related('store').get(user=request.user, is_active=True)
    except StoreManager.DoesNotExist:
        # Check if user is a store owner - auto-create manager for store owners
        from stores.models import Store
        try:
            store = Store.objects.get(owner=request.user, is_active=True)
            # Auto-create manager for store owner
            manager = StoreManager.objects.create(
                user=request.user,
                store=store,
                role='manager',
                can_manage_kg=True if store.market in ['KG', 'ALL'] else False,
                can_manage_us=True if store.market in ['US', 'ALL'] else False,
                can_view_orders=True,
                can_edit_orders=True,
                can_cancel_orders=True,
                can_view_revenue=True,
                is_active=True,
            )
            return manager
        except Store.DoesNotExist:
            return None


# Helper function to check manager permissions
def check_manager_permission(manager, market, permission_type):
    """Check if manager has permission to perform action"""
    if not manager:
        return False
    
    # Check market access
    if market == 'KG' and not manager.can_manage_kg:
        return False
    if market == 'US' and not manager.can_manage_us:
        return False
    
    # Check permission type
    if permission_type == 'view_orders' and not manager.can_view_orders:
        return False
    if permission_type == 'edit_orders' and not manager.can_edit_orders:
        return False
    if permission_type == 'cancel_orders' and not manager.can_cancel_orders:
        return False
    if permission_type == 'view_revenue' and not manager.can_view_revenue:
        return False
    
    return True


# Helper function to check if order belongs to manager's store
def check_order_store_access(manager, order):
    """Check if order belongs to manager's store"""
    if not manager or not manager.store:
        return True  # Platform-wide managers can access all orders
    
    # Check if order contains products from manager's store
    return order.items.filter(
        sku__product__store=manager.store
    ).exists()


# Helper function to filter orders by store
def filter_orders_by_store(queryset, manager):
    """Filter orders queryset by manager's store"""
    if manager and manager.store:
        return queryset.filter(
            items__sku__product__store=manager.store
        ).distinct()
    return queryset


# Helper function to map backend status to frontend display
def get_status_display(status_value):
    """Map backend status to frontend display name"""
    status_map = {
        'pending': 'В ожидании',
        'confirmed': 'ОФОРМЛЕН',
        'processing': 'В ПУТИ',
        'shipped': 'В ПУТИ',
        'delivered': 'ДОСТАВЛЕН',
        'cancelled': 'ОТМЕНЕН',
        'refunded': 'ОТМЕНЕН',
    }
    return status_map.get(status_value, status_value)


# Helper function to get status color
def get_status_color(status_value):
    """Get status color class for frontend"""
    color_map = {
        'pending': 'bg-yellow-100 text-yellow-800',
        'confirmed': 'bg-blue-100 text-blue-800',
        'processing': 'bg-yellow-100 text-yellow-800',
        'shipped': 'bg-yellow-100 text-yellow-800',
        'delivered': 'bg-purple-100 text-purple-800',
        'cancelled': 'bg-red-100 text-red-800',
        'refunded': 'bg-red-100 text-red-800',
    }
    return color_map.get(status_value, 'bg-gray-100 text-gray-800')


# Helper function to map frontend status filter to backend statuses
def map_status_filter(status_filter):
    """Map frontend status filter to backend statuses"""
    if status_filter == 'Все':
        return None
    elif status_filter == 'Ожидание':
        return ['pending', 'confirmed']
    elif status_filter == 'В пути':
        return ['processing', 'shipped']
    elif status_filter == 'Доставлено':
        return ['delivered']
    return None


MARKET_PARAM = OpenApiParameter(
    name='market',
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    description='Market filter (KG or US)',
    required=False,
    enum=['KG', 'US']
)

STATUS_FILTER_PARAM = OpenApiParameter(
    name='status',
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    description='Status filter (Все, Ожидание, В пути, Доставлено)',
    required=False,
    enum=['Все', 'Ожидание', 'В пути', 'Доставлено']
)

SEARCH_PARAM = OpenApiParameter(
    name='search',
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    description='Search query (order number, phone, address)',
    required=False
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


@extend_schema(
    summary="Check manager status",
    description="Check if the current user is a store manager and return manager information",
    responses={
        200: ManagerStatusSerializer,
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=["store-manager"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_manager_status(request):
    """
    Check if the current user is a store manager.
    
    Returns:
    - is_manager: Boolean indicating if user is a manager
    - manager_id: Manager ID if user is a manager
    - role: Manager role (admin, manager, viewer)
    - accessible_markets: List of markets the manager can access
    - can_manage_kg: Whether manager can manage KG market
    - can_manage_us: Whether manager can manage US market
    - is_active: Whether manager is active
    """
    manager = get_manager(request)
    
    if not manager:
        return Response({
            'is_manager': False,
            'manager_id': None,
            'role': None,
            'accessible_markets': [],
            'can_manage_kg': False,
            'can_manage_us': False,
            'is_active': False,
        }, status=status.HTTP_200_OK)
    
    # Update last login
    manager.last_login = timezone.now()
    manager.save(update_fields=['last_login'])
    
    # Log activity
    try:
        log_manager_activity(
            manager=manager,
            action_type='login',
            market=None,
            description='Manager logged in',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
        )
    except Exception:
        # Silently fail if logging fails
        pass
    
    return Response({
        'is_manager': True,
        'manager_id': manager.id,
        'role': manager.role,
        'accessible_markets': manager.accessible_markets,
        'can_manage_kg': manager.can_manage_kg,
        'can_manage_us': manager.can_manage_us,
        'is_active': manager.is_active,
    }, status=status.HTTP_200_OK)


@extend_schema(
    summary="Get dashboard statistics",
    description="Get dashboard statistics including orders count and users count",
    parameters=[MARKET_PARAM],
    responses={
        200: DashboardStatsSerializer,
        403: OpenApiResponse(description="Manager not found or no permission"),
    },
    tags=["store-manager"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """
    Get dashboard statistics for store manager.
    
    Returns:
    - today_orders_count: Orders created in last 24 hours
    - all_orders_count: Total orders count
    - active_orders_count: Active orders (pending, confirmed, processing, shipped)
    - total_users_count: Total users count for this market
    - market: Current market filter
    """
    manager = get_manager(request)
    if not manager:
        return Response(
            {'error': 'Manager not found or inactive'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get market from query params or default to manager's first accessible market
    market = request.query_params.get('market', 'KG').upper()
    if market not in ['KG', 'US']:
        market = 'KG'
    
    # Check permission
    if not check_manager_permission(manager, market, 'view_orders'):
        return Response(
            {'error': 'No permission to view orders for this market'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Calculate time 24 hours ago
    twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
    
    # Base queryset - filter by market
    base_queryset = Order.objects.filter(market=market)
    
    # Filter by store if manager is linked to a store
    base_queryset = filter_orders_by_store(base_queryset, manager)
    
    # Get today's orders count (last 24 hours)
    today_orders = base_queryset.filter(
        order_date__gte=twenty_four_hours_ago
    ).count()
    
    # Get all orders count
    all_orders = base_queryset.count()
    
    # Get active orders count (filtered by store if applicable)
    active_orders = base_queryset.filter(
        status__in=['pending', 'confirmed', 'processing', 'shipped']
    ).count()
    
    # Get total users count for this market
    from users.models import User
    total_users = User.objects.filter(location=market).count()
    
    return Response({
        'success': True,
        'today_orders_count': today_orders,
        'all_orders_count': all_orders,
        'active_orders_count': active_orders,
        'total_users_count': total_users,
        'market': market,
    }, status=status.HTTP_200_OK)


@extend_schema(
    summary="Get orders list",
    description="Get orders list with filtering, search, and pagination",
    parameters=[MARKET_PARAM, STATUS_FILTER_PARAM, SEARCH_PARAM, LIMIT_PARAM, OFFSET_PARAM],
    responses={
        200: ManagerOrderListSerializer(many=True),
        403: OpenApiResponse(description="Manager not found or no permission"),
    },
    tags=["store-manager"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def orders_list(request):
    """
    Get orders list with filtering, search, and pagination.
    
    Filters:
    - market: Market filter (KG or US)
    - status: Status filter (Все, Ожидание, В пути, Доставлено)
    - search: Search by order number, phone, or address
    - limit: Number of results per page (default: 20)
    - offset: Number of results to skip (default: 0)
    """
    manager = get_manager(request)
    if not manager:
        return Response(
            {'error': 'Manager not found or inactive'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get market from query params
    market = request.query_params.get('market', 'KG').upper()
    if market not in ['KG', 'US']:
        market = 'KG'
    
    # Check permission
    if not check_manager_permission(manager, market, 'view_orders'):
        return Response(
            {'error': 'No permission to view orders for this market'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get filters
    status_filter = request.query_params.get('status', 'Все')
    search_query = request.query_params.get('search', '')
    limit = int(request.query_params.get('limit', 20))
    offset = int(request.query_params.get('offset', 0))
    
    # Base queryset - filter by market
    queryset = Order.objects.filter(market=market).select_related(
        'shipping_address', 'payment_method_used'
    ).prefetch_related('items__sku__product__store').order_by('-order_date')
    
    # Filter by store if manager is linked to a store
    queryset = filter_orders_by_store(queryset, manager)
    
    # Apply status filter
    statuses = map_status_filter(status_filter)
    if statuses:
        queryset = queryset.filter(status__in=statuses)
    
    # Apply search filter
    if search_query:
        queryset = queryset.filter(
            Q(order_number__icontains=search_query) |
            Q(customer_phone__icontains=search_query) |
            Q(delivery_address__icontains=search_query) |
            Q(customer_name__icontains=search_query)
        )
    
    # Get total count
    total = queryset.count()
    
    # Apply pagination
    orders = queryset[offset:offset + limit]
    
    # Convert queryset to list to preserve order
    orders_list = list(orders)
    
    # Serialize orders
    serializer = ManagerOrderListSerializer(orders_list, many=True, context={'request': request})
    
    # Add frontend-specific fields
    orders_data = []
    for i, order_data in enumerate(serializer.data):
        order_obj = orders_list[i] if i < len(orders_list) else None
        if order_obj:
            # Create a mutable copy of order_data
            order_dict = dict(order_data)
            order_dict['status_display'] = get_status_display(order_obj.status)
            order_dict['status_color'] = get_status_color(order_obj.status)
            # Format date
            if order_dict.get('order_date'):
                order_date = datetime.fromisoformat(order_dict['order_date'].replace('Z', '+00:00'))
                order_dict['date'] = order_date.strftime('%d.%m.%Y')
                order_dict['order_date_formatted'] = order_date.strftime('%d.%m.%Y, %H:%M')
            # Format amount
            order_dict['amount'] = f"{order_dict.get('total_amount', 0)} {order_dict.get('currency', 'сом')}"
            orders_data.append(order_dict)
        else:
            orders_data.append(order_data)
    
    return Response({
        'success': True,
        'orders': orders_data,
        'total': total,
        'limit': limit,
        'offset': offset,
        'has_more': (offset + limit) < total,
    }, status=status.HTTP_200_OK)


@extend_schema(
    summary="Get order detail",
    description="Get detailed information about a specific order",
    parameters=[MARKET_PARAM],
    responses={
        200: ManagerOrderDetailSerializer,
        403: OpenApiResponse(description="Manager not found or no permission"),
        404: OpenApiResponse(description="Order not found"),
    },
    tags=["store-manager"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_detail(request, order_id):
    """
    Get detailed information about a specific order.
    """
    manager = get_manager(request)
    if not manager:
        return Response(
            {'error': 'Manager not found or inactive'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        order = Order.objects.select_related(
            'shipping_address', 'payment_method_used'
        ).prefetch_related('items').get(id=order_id)
    except Order.DoesNotExist:
        return Response(
            {'error': 'Order not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permission for order's market
    if not check_manager_permission(manager, order.market, 'view_orders'):
        return Response(
            {'error': 'No permission to view orders for this market'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Check if order belongs to manager's store
    if not check_order_store_access(manager, order):
        return Response(
            {'error': 'Order does not belong to your store'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Log activity (only if manager has activity logging enabled)
    try:
        log_manager_activity(
            manager=manager,
            action_type='view_order',
            order=order,
            market=order.market,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
        )
    except Exception:
        # Silently fail if logging fails
        pass
    
    # Serialize order
    serializer = ManagerOrderDetailSerializer(order, context={'request': request})
    order_data = serializer.data
    
    # Add frontend-specific fields
    order_data['status_display'] = get_status_display(order.status)
    order_data['status_color'] = get_status_color(order.status)
    # Format date
    if order_data.get('order_date'):
        order_date = datetime.fromisoformat(order_data['order_date'].replace('Z', '+00:00'))
        order_data['order_date_formatted'] = order_date.strftime('%d.%m.%Y, %H:%M')
    # Format amount
    order_data['amount'] = f"{order_data['total_amount']} {order_data.get('currency', 'сом')}"
    
    return Response({
        'success': True,
        'order': order_data,
    }, status=status.HTTP_200_OK)


@extend_schema(
    summary="Update order status",
    description="Update order status",
    request=OrderStatusUpdateSerializer,
    responses={
        200: ManagerOrderDetailSerializer,
        400: OpenApiResponse(description="Validation error"),
        403: OpenApiResponse(description="Manager not found or no permission"),
        404: OpenApiResponse(description="Order not found"),
    },
    tags=["store-manager"],
)
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_order_status(request, order_id):
    """
    Update order status.
    """
    manager = get_manager(request)
    if not manager:
        return Response(
            {'error': 'Manager not found or inactive'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response(
            {'error': 'Order not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permission
    if not check_manager_permission(manager, order.market, 'edit_orders'):
        return Response(
            {'error': 'No permission to edit orders for this market'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Check if order belongs to manager's store
    if not check_order_store_access(manager, order):
        return Response(
            {'error': 'Order does not belong to your store'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Validate request data
    serializer = OrderStatusUpdateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Get old status
    old_status = order.status
    new_status = serializer.validated_data['status']
    
    # Update status
    order.status = new_status
    
    # Update status-specific timestamps
    now = timezone.now()
    if new_status == 'confirmed' and not order.confirmed_date:
        order.confirmed_date = now
    elif new_status == 'shipped' and not order.shipped_date:
        order.shipped_date = now
    elif new_status == 'delivered' and not order.delivered_date:
        order.delivered_date = now
    elif new_status == 'cancelled' and not order.cancelled_date:
        order.cancelled_date = now
    
    order.save()
    
    # Log activity
    try:
        log_manager_activity(
            manager=manager,
            action_type='update_status',
            order=order,
            market=order.market,
            old_value=old_status,
            new_value=new_status,
            description=f"Order status changed from {old_status} to {new_status}",
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
        )
    except Exception:
        # Silently fail if logging fails
        pass
    
    # Serialize and return updated order
    serializer = ManagerOrderDetailSerializer(order, context={'request': request})
    order_data = serializer.data
    order_data['status_display'] = get_status_display(order.status)
    order_data['status_color'] = get_status_color(order.status)
    
    return Response({
        'success': True,
        'message': 'Order status updated successfully',
        'order': order_data,
    }, status=status.HTTP_200_OK)


@extend_schema(
    summary="Cancel order",
    description="Cancel an order",
    responses={
        200: SuccessMessageSerializer,
        403: OpenApiResponse(description="Manager not found or no permission"),
        404: OpenApiResponse(description="Order not found"),
    },
    tags=["store-manager"],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_order(request, order_id):
    """
    Cancel an order.
    """
    manager = get_manager(request)
    if not manager:
        return Response(
            {'error': 'Manager not found or inactive'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        order = Order.objects.prefetch_related('items__sku__product__store').get(id=order_id)
    except Order.DoesNotExist:
        return Response(
            {'error': 'Order not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permission
    if not check_manager_permission(manager, order.market, 'cancel_orders'):
        return Response(
            {'error': 'No permission to cancel orders for this market'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Check if order belongs to manager's store
    if not check_order_store_access(manager, order):
        return Response(
            {'error': 'Order does not belong to your store'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Check if order can be cancelled
    if not order.can_cancel:
        return Response(
            {'error': 'Order cannot be cancelled'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get old status
    old_status = order.status
    
    # Cancel order
    order.status = 'cancelled'
    order.cancelled_date = timezone.now()
    order.save()
    
    # Log activity
    try:
        log_manager_activity(
            manager=manager,
            action_type='cancel_order',
            order=order,
            market=order.market,
            old_value=old_status,
            new_value='cancelled',
            description=f"Order cancelled by manager",
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
        )
    except Exception:
        # Silently fail if logging fails
        pass
    
    return Response({
        'success': True,
        'message': 'Order cancelled successfully',
    }, status=status.HTTP_200_OK)


@extend_schema(
    summary="Resume order",
    description="Resume a cancelled order",
    responses={
        200: SuccessMessageSerializer,
        403: OpenApiResponse(description="Manager not found or no permission"),
        404: OpenApiResponse(description="Order not found"),
    },
    tags=["store-manager"],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def resume_order(request, order_id):
    """
    Resume a cancelled order (change status back to pending or confirmed).
    """
    manager = get_manager(request)
    if not manager:
        return Response(
            {'error': 'Manager not found or inactive'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        order = Order.objects.prefetch_related('items__sku__product__store').get(id=order_id)
    except Order.DoesNotExist:
        return Response(
            {'error': 'Order not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permission
    if not check_manager_permission(manager, order.market, 'edit_orders'):
        return Response(
            {'error': 'No permission to edit orders for this market'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Check if order belongs to manager's store
    if not check_order_store_access(manager, order):
        return Response(
            {'error': 'Order does not belong to your store'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Check if order is cancelled
    if order.status != 'cancelled':
        return Response(
            {'error': 'Order is not cancelled'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get old status
    old_status = order.status
    
    # Resume order (set to pending)
    order.status = 'pending'
    order.cancelled_date = None
    order.save()
    
    # Log activity
    try:
        log_manager_activity(
            manager=manager,
            action_type='resume_order',
            order=order,
            market=order.market,
            old_value=old_status,
            new_value='pending',
            description=f"Order resumed by manager",
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
        )
    except Exception:
        # Silently fail if logging fails
        pass
    
    return Response({
        'success': True,
        'message': 'Order resumed successfully',
    }, status=status.HTTP_200_OK)


@extend_schema(
    summary="Get revenue analytics",
    description="Get revenue analytics including today's revenue, hourly breakdown, and changes",
    parameters=[MARKET_PARAM],
    responses={
        200: RevenueAnalyticsSerializer,
        403: OpenApiResponse(description="Manager not found or no permission"),
    },
    tags=["store-manager"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def revenue_analytics(request):
    """
    Get revenue analytics for store manager.
    
    Returns:
    - total_revenue: Today's total revenue
    - revenue_change: Change percentage vs yesterday
    - total_orders: Today's total orders
    - orders_change: Change vs yesterday
    - average_order: Average order value
    - average_change: Change percentage vs yesterday
    - hourly_revenue: Hourly revenue breakdown
    - recent_orders: Recent orders for revenue view
    """
    manager = get_manager(request)
    if not manager:
        return Response(
            {'error': 'Manager not found or inactive'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get market from query params
    market = request.query_params.get('market', 'KG').upper()
    if market not in ['KG', 'US']:
        market = 'KG'
    
    # Check permission
    if not check_manager_permission(manager, market, 'view_revenue'):
        return Response(
            {'error': 'No permission to view revenue for this market'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Base queryset for orders - filter by market
    base_orders_queryset = Order.objects.filter(market=market)
    
    # Filter by store if manager is linked to a store
    base_orders_queryset = filter_orders_by_store(base_orders_queryset, manager)
    
    # Calculate today's revenue from filtered orders
    today = timezone.now().date()
    today_orders = base_orders_queryset.filter(order_date__date=today)
    
    today_total_revenue = sum(order.total_amount for order in today_orders)
    today_orders_count = today_orders.count()
    today_avg_order = (today_total_revenue / today_orders_count) if today_orders_count > 0 else Decimal('0')
    
    # Get hourly revenue breakdown from filtered orders
    hourly_revenue = []
    for hour in range(24):
        hour_start = timezone.now().replace(hour=hour, minute=0, second=0, microsecond=0)
        hour_end = hour_start + timedelta(hours=1)
        hour_orders = base_orders_queryset.filter(
            order_date__gte=hour_start,
            order_date__lt=hour_end
        )
        hour_revenue = sum(order.total_amount for order in hour_orders)
        hourly_revenue.append({
            'hour': hour,
            'revenue': str(hour_revenue),
        })
    
    # Get recent orders (last 10) from filtered queryset
    recent_orders_qs = base_orders_queryset.order_by('-order_date')[:10]
    recent_orders = []
    for order in recent_orders_qs:
        order_date = order.order_date
        formatted_time = order_date.strftime('%H:%M') if order_date else ''
        formatted_date = order_date.strftime('%d.%m.%Y') if order_date else ''
        
        recent_orders.append({
            'id': f"#{order.id}",
            'order_number': order.order_number,
            'status': get_status_display(order.status),
            'status_color': get_status_color(order.status),
            'phone': order.customer_phone,
            'address': order.delivery_address,
            'amount': f"{order.total_amount} {order.currency}",
            'created_at': order_date.isoformat() if order_date else '',
            'time': formatted_time,
            'date': formatted_date,
        })
    
    # Calculate revenue change vs yesterday
    yesterday = timezone.now().date() - timedelta(days=1)
    yesterday_orders = base_orders_queryset.filter(order_date__date=yesterday)
    yesterday_total_revenue = sum(order.total_amount for order in yesterday_orders)
    yesterday_orders_count = yesterday_orders.count()
    yesterday_avg_order = (yesterday_total_revenue / yesterday_orders_count) if yesterday_orders_count > 0 else Decimal('0')
    
    revenue_change = "+0% чем вчера"
    if yesterday_total_revenue > 0:
        change_percent = ((today_total_revenue - yesterday_total_revenue) / yesterday_total_revenue) * 100
        if change_percent > 0:
            revenue_change = f"+{change_percent:.0f}% чем вчера"
        else:
            revenue_change = f"{change_percent:.0f}% чем вчера"
    elif yesterday_total_revenue == 0 and today_total_revenue > 0:
        revenue_change = "+100% чем вчера"
    
    # Calculate orders change
    orders_change = "0 чем вчера"
    orders_diff = today_orders_count - yesterday_orders_count
    if orders_diff > 0:
        orders_change = f"+{orders_diff} чем вчера"
    elif orders_diff < 0:
        orders_change = f"{orders_diff} чем вчера"
    
    # Calculate average change
    average_change = "+0% чем вчера"
    if yesterday_avg_order > 0:
        avg_change_percent = ((today_avg_order - yesterday_avg_order) / yesterday_avg_order) * 100
        if avg_change_percent > 0:
            average_change = f"+{avg_change_percent:.0f}% чем вчера"
        else:
            average_change = f"{avg_change_percent:.0f}% чем вчера"
    elif yesterday_avg_order == 0 and today_avg_order > 0:
        average_change = "+100% чем вчера"
    
    # Get currency info
    currency = 'сом' if market == 'KG' else '$'
    currency_code = 'KGS' if market == 'KG' else 'USD'
    
    return Response({
        'success': True,
        'total_revenue': f"{today_total_revenue} {currency_code}",
        'revenue_change': revenue_change,
        'total_orders': today_orders_count,
        'orders_change': orders_change,
        'average_order': f"{today_avg_order} {currency_code}",
        'average_change': average_change,
        'currency': currency,
        'currency_code': currency_code,
        'hourly_revenue': hourly_revenue,
        'recent_orders': recent_orders,
    }, status=status.HTTP_200_OK)
