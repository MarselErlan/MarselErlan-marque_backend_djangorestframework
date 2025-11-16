"""
Serializers for Orders App
"""

from rest_framework import serializers
from .models import Order, OrderItem
from users.models import Address, PaymentMethod
from products.models import Cart, CartItem, SKU


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for order items"""
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product_name', 'product_brand', 'size', 'color',
            'price', 'quantity', 'subtotal', 'image_url'
        ]
        read_only_fields = ['id', 'subtotal']


class OrderCreateSerializer(serializers.Serializer):
    """Serializer for creating orders"""
    
    customer_name = serializers.CharField(max_length=255)
    customer_phone = serializers.CharField(max_length=20)
    customer_email = serializers.EmailField(required=False, allow_blank=True)
    
    delivery_address = serializers.CharField()
    delivery_city = serializers.CharField(required=False, allow_blank=True)
    delivery_state = serializers.CharField(required=False, allow_blank=True)
    delivery_postal_code = serializers.CharField(required=False, allow_blank=True)
    delivery_notes = serializers.CharField(required=False, allow_blank=True)
    requested_delivery_date = serializers.DateField(required=False, allow_null=True)
    
    shipping_address_id = serializers.IntegerField(required=False, allow_null=True)
    payment_method_used_id = serializers.IntegerField(required=False, allow_null=True)
    
    payment_method = serializers.ChoiceField(choices=Order.PAYMENT_METHOD_CHOICES, default='cash')
    
    shipping_cost = serializers.DecimalField(max_digits=10, decimal_places=2, default=350, required=False)
    tax = serializers.DecimalField(max_digits=10, decimal_places=2, default=0, required=False)
    
    use_cart = serializers.BooleanField(default=True)
    
    def validate_shipping_address_id(self, value):
        if value:
            request = self.context.get('request')
            if request and request.user.is_authenticated:
                try:
                    address = Address.objects.get(id=value, user=request.user)
                    return value
                except Address.DoesNotExist:
                    raise serializers.ValidationError("Address not found or doesn't belong to user")
        return value
    
    def validate_payment_method_used_id(self, value):
        if value:
            request = self.context.get('request')
            if request and request.user.is_authenticated:
                try:
                    payment = PaymentMethod.objects.get(id=value, user=request.user)
                    return value
                except PaymentMethod.DoesNotExist:
                    raise serializers.ValidationError("Payment method not found or doesn't belong to user")
        return value


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for order details"""
    
    items = OrderItemSerializer(many=True, read_only=True)
    items_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status', 'customer_name', 'customer_phone',
            'delivery_address', 'delivery_city', 'delivery_state', 'delivery_postal_code',
            'delivery_country', 'delivery_notes', 'requested_delivery_date',
            'payment_method', 'payment_status',
            'subtotal', 'shipping_cost', 'tax', 'total_amount', 'currency', 'currency_code',
            'order_date', 'items', 'items_count'
        ]
        read_only_fields = ['id', 'order_number', 'order_date']

