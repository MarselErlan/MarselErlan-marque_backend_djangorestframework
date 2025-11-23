"""
Serializers for Orders App
"""

from rest_framework import serializers
from .models import Order, OrderItem, Review, ReviewImage
from users.models import Address, PaymentMethod
from products.models import Cart, CartItem, SKU, Product


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for order items"""
    
    product_id = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product_id', 'product_name', 'product_brand', 'size', 'color',
            'price', 'quantity', 'subtotal', 'image_url'
        ]
        read_only_fields = ['id', 'subtotal']
    
    def get_product_id(self, obj):
        """Get product_id from SKU if available"""
        if obj.sku and obj.sku.product:
            return obj.sku.product.id
        return None


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
    
    currency = serializers.CharField(max_length=10, required=False, allow_blank=True, help_text="Currency symbol (e.g., $, сом)")
    currency_code = serializers.CharField(max_length=3, required=False, allow_blank=True, help_text="ISO 4217 currency code (e.g., USD, KGS)")
    
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


class ReviewImageSerializer(serializers.ModelSerializer):
    """Serializer for review images"""
    
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ReviewImage
        fields = ['id', 'image', 'image_url', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_image_url(self, obj):
        """Return the image URL if image exists"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return obj.image_url


class ReviewCreateSerializer(serializers.Serializer):
    """Serializer for creating reviews with images"""
    
    order_id = serializers.IntegerField(required=True)
    product_id = serializers.IntegerField(required=True)
    rating = serializers.IntegerField(min_value=1, max_value=5, required=True)
    comment = serializers.CharField(required=True, allow_blank=False)
    title = serializers.CharField(required=False, allow_blank=True, max_length=255)
    # Note: images are handled separately in the view, not validated here
    # to avoid issues with multipart/form-data file handling
    
    def validate_order_id(self, value):
        """Validate that the order exists and belongs to the user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                order = Order.objects.get(id=value, user=request.user)
                return value
            except Order.DoesNotExist:
                raise serializers.ValidationError("Order not found or doesn't belong to user")
        raise serializers.ValidationError("Authentication required")
    
    def validate_product_id(self, value):
        """Validate that the product exists"""
        try:
            product = Product.objects.get(id=value)
            return value
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found")
    
    def validate(self, data):
        """Validate that the product is in the order"""
        order_id = data.get('order_id')
        product_id = data.get('product_id')
        
        if order_id and product_id:
            try:
                order = Order.objects.get(id=order_id, user=self.context['request'].user)
                # Check if product is in order items
                order_items = order.items.filter(sku__product_id=product_id)
                if not order_items.exists():
                    raise serializers.ValidationError({
                        'product_id': 'This product is not in the specified order'
                    })
            except Order.DoesNotExist:
                pass  # Already validated in validate_order_id
        
        return data


class ReviewSerializer(serializers.ModelSerializer):
    """Serializer for review details"""
    
    images = ReviewImageSerializer(many=True, read_only=True)
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Review
        fields = [
            'id', 'user', 'product', 'order', 'rating', 'title', 'comment',
            'is_verified_purchase', 'is_approved', 'created_at', 'updated_at',
            'images', 'user_name'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at', 'is_verified_purchase', 'is_approved']
    
    def get_user_name(self, obj):
        """Return user's full name or phone"""
        if obj.user and obj.user.full_name:
            return obj.user.full_name
        if obj.user and obj.user.phone:
            return obj.user.phone
        return "Покупатель"

