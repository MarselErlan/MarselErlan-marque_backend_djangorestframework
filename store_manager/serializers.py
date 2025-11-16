"""
Serializers for Store Manager App
"""

from rest_framework import serializers
from orders.models import Order, OrderItem
from .models import StoreManager, ManagerSettings, RevenueSnapshot, ManagerActivityLog, ManagerNotification
from users.models import User


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for order items in manager views"""
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product_name', 'product_brand', 'size', 'color',
            'price', 'quantity', 'subtotal', 'image_url'
        ]
        read_only_fields = ['id', 'subtotal']


class ManagerOrderListSerializer(serializers.ModelSerializer):
    """Serializer for order list in manager dashboard"""
    
    items_count = serializers.IntegerField(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status', 'customer_name', 'customer_phone',
            'delivery_address', 'delivery_city', 'total_amount', 'currency',
            'order_date', 'requested_delivery_date', 'items_count', 'items'
        ]
        read_only_fields = ['id', 'order_number', 'order_date']


class ManagerOrderDetailSerializer(serializers.ModelSerializer):
    """Serializer for order detail in manager dashboard"""
    
    items = OrderItemSerializer(many=True, read_only=True)
    items_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status', 'customer_name', 'customer_phone',
            'customer_email', 'delivery_address', 'delivery_city', 'delivery_state',
            'delivery_postal_code', 'delivery_country', 'delivery_notes',
            'requested_delivery_date',
            'payment_method', 'payment_status', 'card_type', 'card_last_four',
            'subtotal', 'shipping_cost', 'tax', 'total_amount', 'currency', 'currency_code',
            'order_date', 'confirmed_date', 'shipped_date', 'delivered_date',
            'items', 'items_count'
        ]
        read_only_fields = ['id', 'order_number', 'order_date']


class OrderStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating order status"""
    
    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES)
    
    def validate_status(self, value):
        """Validate status transition"""
        # Add any business logic for status transitions here
        return value


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics"""
    
    today_orders_count = serializers.IntegerField()
    all_orders_count = serializers.IntegerField()
    active_orders_count = serializers.IntegerField()
    market = serializers.CharField()


class RevenueAnalyticsSerializer(serializers.Serializer):
    """Serializer for revenue analytics"""
    
    total_revenue = serializers.CharField()
    revenue_change = serializers.CharField()
    total_orders = serializers.IntegerField()
    orders_change = serializers.CharField()
    average_order = serializers.CharField()
    average_change = serializers.CharField()
    currency = serializers.CharField()
    currency_code = serializers.CharField()
    hourly_revenue = serializers.ListField(
        child=serializers.DictField(
            child=serializers.CharField()
        )
    )
    recent_orders = serializers.ListField(
        child=serializers.DictField()
    )


class HourlyRevenueSerializer(serializers.Serializer):
    """Serializer for hourly revenue data"""
    
    time = serializers.CharField()
    amount = serializers.CharField()
    is_highlighted = serializers.BooleanField(required=False)


class RecentOrderSerializer(serializers.Serializer):
    """Serializer for recent orders in revenue view"""
    
    id = serializers.CharField()
    order_number = serializers.CharField()
    status = serializers.CharField()
    status_color = serializers.CharField()
    phone = serializers.CharField()
    address = serializers.CharField()
    amount = serializers.CharField()
    created_at = serializers.DateTimeField()


class SuccessMessageSerializer(serializers.Serializer):
    """Generic success response with message"""
    
    success = serializers.BooleanField()
    message = serializers.CharField()


class ManagerStatusSerializer(serializers.Serializer):
    """Serializer for manager status check"""
    
    is_manager = serializers.BooleanField()
    manager_id = serializers.IntegerField(required=False, allow_null=True)
    role = serializers.CharField(required=False, allow_null=True)
    accessible_markets = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_null=True
    )
    can_manage_kg = serializers.BooleanField(required=False)
    can_manage_us = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)

