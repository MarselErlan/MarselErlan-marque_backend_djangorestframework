"""
Utility functions for store manager operations and analytics
"""
from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone
from datetime import datetime, timedelta, date
from decimal import Decimal
from .models import RevenueSnapshot, ManagerActivityLog, ManagerNotification
from orders.models import Order
from users.models import Address, PaymentMethod


def calculate_revenue_snapshot(market='KG', snapshot_date=None, snapshot_hour=None):
    """
    Calculate revenue metrics for a specific period
    
    Args:
        market: Market code ('KG' or 'US')
        snapshot_date: Date for the snapshot (default: today)
        snapshot_hour: Hour for hourly snapshot (0-23, None for daily)
    
    Returns:
        Dictionary with revenue metrics
    """
    if snapshot_date is None:
        snapshot_date = timezone.now().date()
    
    # Get currency info based on market
    currency_info = {
        'KG': {'symbol': 'сом', 'code': 'KGS'},
        'US': {'symbol': '$', 'code': 'USD'}
    }
    currency = currency_info.get(market, currency_info['KG'])
    
    # Build query filters (using direct market field for performance)
    filters = Q(market=market, order_date__date=snapshot_date)
    
    if snapshot_hour is not None:
        filters &= Q(order_date__hour=snapshot_hour)
    
    # Get orders
    orders = Order.objects.filter(filters)
    
    # Calculate metrics
    metrics = orders.aggregate(
        total_revenue=Sum('total_amount'),
        total_orders=Count('id'),
        completed_orders=Count('id', filter=Q(status='delivered')),
        cancelled_orders=Count('id', filter=Q(status='cancelled')),
        pending_orders=Count('id', filter=Q(status__in=['pending', 'confirmed', 'processing', 'shipped'])),
        average_order=Avg('total_amount')
    )
    
    return {
        'market': market,
        'snapshot_date': snapshot_date,
        'snapshot_hour': snapshot_hour,
        'total_revenue': metrics['total_revenue'] or Decimal('0'),
        'currency': currency['symbol'],
        'currency_code': currency['code'],
        'total_orders': metrics['total_orders'] or 0,
        'completed_orders': metrics['completed_orders'] or 0,
        'cancelled_orders': metrics['cancelled_orders'] or 0,
        'pending_orders': metrics['pending_orders'] or 0,
        'average_order_value': metrics['average_order'] or Decimal('0'),
    }


def create_or_update_revenue_snapshot(market='KG', snapshot_type='daily', snapshot_date=None, snapshot_hour=None):
    """
    Create or update a revenue snapshot in the database
    
    Args:
        market: Market code ('KG' or 'US')
        snapshot_type: Type of snapshot ('hourly', 'daily', 'weekly', 'monthly')
        snapshot_date: Date for the snapshot
        snapshot_hour: Hour for hourly snapshot
    
    Returns:
        RevenueSnapshot instance
    """
    if snapshot_date is None:
        snapshot_date = timezone.now().date()
    
    # Calculate metrics
    metrics = calculate_revenue_snapshot(market, snapshot_date, snapshot_hour)
    
    # Calculate change percentages (compare with previous period)
    previous_snapshot = get_previous_snapshot(market, snapshot_type, snapshot_date, snapshot_hour)
    revenue_change = None
    orders_change = None
    
    if previous_snapshot:
        if previous_snapshot.total_revenue > 0:
            revenue_change = ((metrics['total_revenue'] - previous_snapshot.total_revenue) / previous_snapshot.total_revenue) * 100
        if previous_snapshot.total_orders > 0:
            orders_change = ((metrics['total_orders'] - previous_snapshot.total_orders) / previous_snapshot.total_orders) * 100
    
    # Create or update snapshot
    snapshot, created = RevenueSnapshot.objects.update_or_create(
        market=market,
        snapshot_type=snapshot_type,
        snapshot_date=snapshot_date,
        snapshot_hour=snapshot_hour,
        defaults={
            'total_revenue': metrics['total_revenue'],
            'currency': metrics['currency'],
            'currency_code': metrics['currency_code'],
            'total_orders': metrics['total_orders'],
            'completed_orders': metrics['completed_orders'],
            'cancelled_orders': metrics['cancelled_orders'],
            'pending_orders': metrics['pending_orders'],
            'average_order_value': metrics['average_order_value'],
            'revenue_change_percent': revenue_change,
            'orders_change_percent': orders_change,
        }
    )
    
    return snapshot


def get_previous_snapshot(market, snapshot_type, snapshot_date, snapshot_hour=None):
    """Get the previous snapshot for comparison"""
    if snapshot_type == 'hourly' and snapshot_hour is not None:
        # Previous hour
        if snapshot_hour == 0:
            prev_date = snapshot_date - timedelta(days=1)
            prev_hour = 23
        else:
            prev_date = snapshot_date
            prev_hour = snapshot_hour - 1
        
        return RevenueSnapshot.objects.filter(
            market=market,
            snapshot_type=snapshot_type,
            snapshot_date=prev_date,
            snapshot_hour=prev_hour
        ).first()
    
    elif snapshot_type == 'daily':
        # Previous day
        prev_date = snapshot_date - timedelta(days=1)
        return RevenueSnapshot.objects.filter(
            market=market,
            snapshot_type=snapshot_type,
            snapshot_date=prev_date
        ).first()
    
    return None


def get_today_revenue(market='KG'):
    """Get today's revenue data"""
    today = timezone.now().date()
    snapshot = RevenueSnapshot.objects.filter(
        market=market,
        snapshot_type='daily',
        snapshot_date=today
    ).first()
    
    if snapshot:
        return {
            'total_revenue': str(snapshot.total_revenue),
            'revenue_change': f"+{snapshot.revenue_change_percent}% чем вчера" if snapshot.revenue_change_percent and snapshot.revenue_change_percent > 0 else f"{snapshot.revenue_change_percent}% чем вчера",
            'total_orders': snapshot.total_orders,
            'orders_change': f"{snapshot.orders_change_percent:+.0f} чем вчера" if snapshot.orders_change_percent else "0 чем вчера",
            'average_order': str(snapshot.average_order_value),
            'currency': snapshot.currency_code
        }
    
    # If no snapshot exists, calculate on the fly
    metrics = calculate_revenue_snapshot(market, today)
    return {
        'total_revenue': str(metrics['total_revenue']),
        'revenue_change': "+0% чем вчера",
        'total_orders': metrics['total_orders'],
        'orders_change': "0 чем вчера",
        'average_order': str(metrics['average_order_value']),
        'currency': metrics['currency_code']
    }


def get_hourly_revenue(market='KG', date=None):
    """Get hourly revenue breakdown for a specific date"""
    if date is None:
        date = timezone.now().date()
    
    hourly_data = []
    current_hour = timezone.now().hour if date == timezone.now().date() else 23
    
    for hour in range(0, current_hour + 1):
        snapshot = RevenueSnapshot.objects.filter(
            market=market,
            snapshot_type='hourly',
            snapshot_date=date,
            snapshot_hour=hour
        ).first()
        
        if snapshot:
            hourly_data.append({
                'time': f"{hour:02d}:00",
                'amount': f"{snapshot.total_revenue} {snapshot.currency_code}",
                'is_highlighted': hour == current_hour
            })
    
    return hourly_data


def log_manager_activity(manager, action_type, order=None, market=None, description=None, 
                         old_value=None, new_value=None, ip_address=None, user_agent=None):
    """
    Log manager activity for audit purposes
    
    Args:
        manager: StoreManager instance
        action_type: Type of action (from ManagerActivityLog.ACTION_TYPE_CHOICES)
        order: Related Order instance (optional)
        market: Market where action was performed
        description: Additional description
        old_value: Previous value (for updates)
        new_value: New value (for updates)
        ip_address: IP address of the manager
        user_agent: User agent string
    
    Returns:
        ManagerActivityLog instance
    """
    log = ManagerActivityLog.objects.create(
        manager=manager,
        action_type=action_type,
        order=order,
        market=market,
        description=description,
        old_value=old_value,
        new_value=new_value,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    return log


def notify_manager(manager, notification_type, title, message, order=None, 
                  market=None, priority='medium', action_url=None):
    """
    Send notification to a manager
    
    Args:
        manager: StoreManager instance
        notification_type: Type of notification
        title: Notification title
        message: Notification message
        order: Related Order instance (optional)
        market: Related market
        priority: Priority level ('low', 'medium', 'high', 'urgent')
        action_url: URL for action button
    
    Returns:
        ManagerNotification instance
    """
    # Check if manager has notifications enabled for this type
    settings = manager.settings
    
    if notification_type == 'new_order' and not settings.notify_new_orders:
        return None
    if notification_type == 'status_change' and not settings.notify_status_changes:
        return None
    if notification_type == 'delivery_error' and not settings.notify_delivery_errors:
        return None
    
    notification = ManagerNotification.objects.create(
        manager=manager,
        notification_type=notification_type,
        priority=priority,
        title=title,
        message=message,
        order=order,
        market=market,
        action_url=action_url
    )
    
    return notification


def get_active_orders_count(market='KG'):
    """Get count of active orders (pending, confirmed, processing, shipped)
    
    Note: Uses direct market field on Order for better performance
    """
    count = Order.objects.filter(
        market=market,
        status__in=['pending', 'confirmed', 'processing', 'shipped']
    ).count()
    
    return count


def get_today_orders(market='KG'):
    """Get today's orders
    
    Note: Uses direct market field on Order for better performance
    """
    today = timezone.now().date()
    orders = Order.objects.filter(
        market=market,
        order_date__date=today
    ).order_by('-order_date')
    
    return orders


def get_recent_orders(market='KG', limit=10):
    """Get recent orders for dashboard
    
    Note: Uses direct market field on Order for better performance
    """
    orders = Order.objects.filter(
        market=market
    ).order_by('-order_date')[:limit]
    
    return orders


def filter_orders_by_status(queryset, status_filter):
    """
    Filter orders by status
    
    Args:
        queryset: Order queryset
        status_filter: Filter string ('Все', 'Ожидание', 'В пути', 'Доставлено')
    
    Returns:
        Filtered queryset
    """
    if status_filter == 'Все':
        return queryset
    elif status_filter == 'Ожидание':
        return queryset.filter(status__in=['pending', 'confirmed'])
    elif status_filter == 'В пути':
        return queryset.filter(status__in=['processing', 'shipped'])
    elif status_filter == 'Доставлено':
        return queryset.filter(status='delivered')
    
    return queryset


# ==========================================
# ENHANCED ANALYTICS (Using Order References)
# ==========================================

def get_payment_method_analytics(market='KG', date_from=None, date_to=None):
    """
    Analyze payment method usage
    
    Returns breakdown of:
    - Payment type distribution (card, cash, bank_transfer, digital_wallet)
    - Card type distribution (visa, mastercard, mir, amex)
    - Total revenue per payment method
    
    Uses the new payment snapshot fields on Order model
    """
    if date_from is None:
        date_from = timezone.now().date() - timedelta(days=30)
    if date_to is None:
        date_to = timezone.now().date()
    
    orders = Order.objects.filter(
        market=market,
        order_date__date__gte=date_from,
        order_date__date__lte=date_to,
        status__in=['delivered', 'processing', 'shipped']  # Exclude cancelled
    )
    
    # Payment type breakdown
    payment_types = orders.values('payment_method').annotate(
        count=Count('id'),
        revenue=Sum('total_amount')
    ).order_by('-count')
    
    # Card type breakdown (only for card payments)
    card_types = orders.filter(
        payment_method='card'
    ).values('card_type').annotate(
        count=Count('id'),
        revenue=Sum('total_amount')
    ).order_by('-count')
    
    # Get currency
    currency = 'сом' if market == 'KG' else '$'
    
    return {
        'market': market,
        'date_from': date_from,
        'date_to': date_to,
        'currency': currency,
        'payment_types': list(payment_types),
        'card_types': list(card_types),
        'total_orders': orders.count(),
    }


def get_delivery_location_analytics(market='KG', date_from=None, date_to=None, top_n=10):
    """
    Analyze delivery locations
    
    Returns:
    - Top cities by order count
    - Top cities by revenue
    - State breakdown (for US market)
    
    Uses the new delivery snapshot fields on Order model
    """
    if date_from is None:
        date_from = timezone.now().date() - timedelta(days=30)
    if date_to is None:
        date_to = timezone.now().date()
    
    orders = Order.objects.filter(
        market=market,
        order_date__date__gte=date_from,
        order_date__date__lte=date_to,
        status__in=['delivered', 'processing', 'shipped']
    )
    
    # City breakdown
    cities = orders.values('delivery_city').annotate(
        count=Count('id'),
        revenue=Sum('total_amount')
    ).order_by('-count')[:top_n]
    
    # State breakdown (for US market)
    states = None
    if market == 'US':
        states = orders.filter(
            delivery_state__isnull=False
        ).values('delivery_state').annotate(
            count=Count('id'),
            revenue=Sum('total_amount')
        ).order_by('-count')[:top_n]
    
    # Get currency
    currency = 'сом' if market == 'KG' else '$'
    
    result = {
        'market': market,
        'date_from': date_from,
        'date_to': date_to,
        'currency': currency,
        'top_cities': list(cities),
        'total_orders': orders.count(),
    }
    
    if states:
        result['top_states'] = list(states)
    
    return result


def get_popular_addresses(market='KG', top_n=10):
    """
    Get most frequently used delivery addresses
    
    Uses the shipping_address ForeignKey on Order model
    to find which saved addresses are used most often
    """
    # Get addresses that have been used in orders
    addresses = Address.objects.filter(
        market=market,
        orders_shipped_to__isnull=False
    ).annotate(
        order_count=Count('orders_shipped_to'),
        total_revenue=Sum('orders_shipped_to__total_amount')
    ).order_by('-order_count')[:top_n]
    
    # Get currency
    currency = 'сом' if market == 'KG' else '$'
    
    result = []
    for address in addresses:
        result.append({
            'address_id': address.id,
            'title': address.title,
            'city': address.city,
            'full_address': address.full_address,
            'order_count': address.order_count,
            'total_revenue': address.total_revenue,
        })
    
    return {
        'market': market,
        'currency': currency,
        'popular_addresses': result,
    }


def get_popular_payment_methods(market='KG', top_n=10):
    """
    Get most frequently used payment methods
    
    Uses the payment_method_used ForeignKey on Order model
    to find which saved payment methods are used most often
    """
    # Get payment methods that have been used in orders
    payment_methods = PaymentMethod.objects.filter(
        market=market,
        orders_paid_with__isnull=False
    ).annotate(
        order_count=Count('orders_paid_with'),
        total_revenue=Sum('orders_paid_with__total_amount')
    ).order_by('-order_count')[:top_n]
    
    # Get currency
    currency = 'сом' if market == 'KG' else '$'
    
    result = []
    for payment in payment_methods:
        result.append({
            'payment_id': payment.id,
            'payment_type': payment.payment_type,
            'card_type': payment.card_type,
            'card_masked': payment.card_number_masked,
            'order_count': payment.order_count,
            'total_revenue': payment.total_revenue,
        })
    
    return {
        'market': market,
        'currency': currency,
        'popular_payment_methods': result,
    }


def get_customer_analytics(market='KG', date_from=None, date_to=None):
    """
    Analyze customer behavior
    
    Returns:
    - Customers by order count
    - Average orders per customer
    - Repeat customer rate
    - Top customers by revenue
    """
    if date_from is None:
        date_from = timezone.now().date() - timedelta(days=30)
    if date_to is None:
        date_to = timezone.now().date()
    
    from users.models import User
    
    # Get users with orders in this market
    customers = User.objects.filter(
        market=market,
        orders__order_date__date__gte=date_from,
        orders__order_date__date__lte=date_to
    ).annotate(
        order_count=Count('orders'),
        total_spent=Sum('orders__total_amount')
    ).order_by('-total_spent')
    
    # Calculate metrics
    total_customers = customers.count()
    repeat_customers = customers.filter(order_count__gt=1).count()
    repeat_rate = (repeat_customers / total_customers * 100) if total_customers > 0 else 0
    
    # Top customers
    top_customers = customers[:10]
    
    # Get currency
    currency = 'сом' if market == 'KG' else '$'
    
    return {
        'market': market,
        'date_from': date_from,
        'date_to': date_to,
        'currency': currency,
        'total_customers': total_customers,
        'repeat_customers': repeat_customers,
        'repeat_rate': round(repeat_rate, 2),
        'top_customers': [
            {
                'user_id': c.id,
                'phone': c.phone,
                'name': c.get_full_name(),
                'order_count': c.order_count,
                'total_spent': c.total_spent,
            }
            for c in top_customers
        ],
    }

