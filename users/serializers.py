"""
Serializers for Users App
Handles serialization/deserialization of User, Address, PaymentMethod, Notification models
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from orders.models import Order, OrderItem
from .models import Address, PaymentMethod, VerificationCode, Notification, UserPhoneNumber

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    formatted_phone = serializers.CharField(source='get_formatted_phone', read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    currency = serializers.CharField(source='get_currency', read_only=True)
    currency_code = serializers.CharField(source='get_currency_code', read_only=True)
    country = serializers.CharField(source='get_country', read_only=True)
    profile_image = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'phone', 'formatted_phone', 'name', 'full_name',
            'profile_image', 'is_active', 'is_verified',
            'location', 'language', 'country', 'currency', 'currency_code',
            'last_login', 'created_at'
        ]
        read_only_fields = ['id', 'is_verified', 'created_at', 'last_login']

    def get_profile_image(self, obj):
        if obj.profile_image:
            request = self.context.get('request')
            url = obj.profile_image.url
            if request:
                return request.build_absolute_uri(url)
            return url
        return None


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile"""
    profile_image = serializers.ImageField(required=False, allow_null=True)
    
    class Meta:
        model = User
        fields = ['full_name', 'profile_image']
        
    def validate_full_name(self, value):
        if value and len(value) < 2:
            raise serializers.ValidationError("Full name must be at least 2 characters long")
        return value


class AddressSerializer(serializers.ModelSerializer):
    """Serializer for Address model"""
    
    class Meta:
        model = Address
        fields = [
            'id', 'user', 'title', 'full_address', 'street', 'building',
            'apartment', 'city', 'state', 'postal_code', 'country',
            'is_default', 'market', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'market', 'country', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        # Auto-set market from user
        user = self.context['request'].user
        validated_data['user'] = user
        validated_data['market'] = user.location
        validated_data['country'] = Address.MARKET_COUNTRY_MAP.get(user.location, 'Kyrgyzstan')
        
        # If this is set as default, unset other defaults
        if validated_data.get('is_default', False):
            Address.objects.filter(user=user, is_default=True).update(is_default=False)
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        market = instance.user.location if instance.user else instance.market
        validated_data['market'] = market
        validated_data['country'] = Address.MARKET_COUNTRY_MAP.get(market, instance.country)
        
        # If this is being set as default, unset other defaults
        if validated_data.get('is_default', False) and not instance.is_default:
            Address.objects.filter(user=instance.user, is_default=True).update(is_default=False)
        
        return super().update(instance, validated_data)


class AddressCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating addresses (no user field required)"""
    
    LOCATION_REQUIRED_FIELDS = {
        'KG': ['title', 'full_address', 'city'],
        'US': ['title', 'full_address', 'street', 'city', 'state', 'postal_code'],
    }
    
    class Meta:
        model = Address
        fields = [
            'title', 'full_address', 'street', 'building', 'apartment',
            'city', 'state', 'postal_code', 'country', 'is_default'
        ]
        read_only_fields = ['country']
    
    def _get_market(self):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            return request.user.location
        if self.instance:
            return self.instance.market
        return 'KG'
    
    def validate(self, attrs):
        market = self._get_market()
        required_fields = self.LOCATION_REQUIRED_FIELDS.get(market, ['title', 'full_address'])
        
        for field in required_fields:
            if field in attrs and attrs[field]:
                continue
            if self.instance and getattr(self.instance, field, None):
                continue
            raise serializers.ValidationError({field: 'This field is required for this market.'})
        
        return attrs
    
    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user if request else None
        if not user:
            raise serializers.ValidationError("Authenticated user is required.")
        
        validated_data['user'] = user
        validated_data['market'] = user.location
        validated_data['country'] = Address.MARKET_COUNTRY_MAP.get(user.location, 'Kyrgyzstan')
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        market = self._get_market()
        validated_data['market'] = market
        validated_data['country'] = Address.MARKET_COUNTRY_MAP.get(market, instance.country)
        return super().update(instance, validated_data)


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Serializer for PaymentMethod model"""
    
    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'user', 'payment_type', 'card_type', 'card_number_masked',
            'card_holder_name', 'expiry_month', 'expiry_year', 'is_default',
            'market', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'card_number_masked', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        # Auto-set market from user
        user = self.context['request'].user
        validated_data['user'] = user
        validated_data['market'] = user.location
        
        # If this is set as default, unset other defaults
        if validated_data.get('is_default', False):
            PaymentMethod.objects.filter(user=user, is_default=True).update(is_default=False)
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        # If this is being set as default, unset other defaults
        if validated_data.get('is_default', False) and not instance.is_default:
            PaymentMethod.objects.filter(user=instance.user, is_default=True).update(is_default=False)
        
        return super().update(instance, validated_data)


class PaymentMethodCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating payment methods"""
    card_number = serializers.CharField(write_only=True, max_length=16, min_length=13)
    
    class Meta:
        model = PaymentMethod
        fields = [
            'card_number', 'card_holder_name', 'expiry_month',
            'expiry_year', 'is_default'
        ]
    
    def validate_card_number(self, value):
        # Remove spaces and hyphens
        card_number = value.replace(' ', '').replace('-', '')
        
        if not card_number.isdigit():
            raise serializers.ValidationError("Card number must contain only digits")
        
        if not (13 <= len(card_number) <= 19):
            raise serializers.ValidationError("Card number must be between 13 and 19 digits")
        
        return card_number
    
    def validate_expiry_month(self, value):
        if not (1 <= int(value) <= 12):
            raise serializers.ValidationError("Month must be between 1 and 12")
        return value

    def validate_expiry_year(self, value):
        from datetime import datetime
        current_year = datetime.now().year
        if int(value) < current_year:
            raise serializers.ValidationError("Card has expired")
        return value


class PhoneNumberSerializer(serializers.ModelSerializer):
    """Serializer for additional phone numbers."""
    
    class Meta:
        model = UserPhoneNumber
        fields = ['id', 'label', 'phone', 'is_primary', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class PhoneNumberCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating phone numbers."""
    
    class Meta:
        model = UserPhoneNumber
        fields = ['label', 'phone', 'is_primary']
    
    def validate_phone(self, value):
        phone = value.replace(' ', '').replace('-', '')
        if not phone:
            raise serializers.ValidationError("Phone number is required.")
        if not phone.startswith('+'):
            raise serializers.ValidationError("Phone number must include country code (e.g., +996...).")
        digits = ''.join(ch for ch in phone if ch.isdigit())
        if len(digits) < 6:
            raise serializers.ValidationError("Phone number is too short.")
        return value
    
class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model"""
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'type', 'title', 'message', 'is_read',
            'order_id', 'market', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for order item snapshots"""
    
    product_id = serializers.SerializerMethodField()
    size = serializers.CharField(read_only=True)
    color = serializers.CharField(read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id',
            'product_id',
            'product_name',
            'quantity',
            'price',
            'subtotal',
            'image_url',
            'size',
            'color',
        ]
    
    def get_product_id(self, obj):
        """Get product_id from SKU if available"""
        if obj.sku and obj.sku.product:
            return obj.sku.product.id
        return None


class OrderListSerializer(serializers.ModelSerializer):
    """Serializer for orders list"""

    items = OrderItemSerializer(many=True, read_only=True)
    items_count = serializers.IntegerField(read_only=True)
    delivery_date = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'status',
            'total_amount',
            'currency',
            'order_date',
            'delivery_date',
            'delivery_address',
            'items_count',
            'items',
        ]

    def get_delivery_date(self, obj):
        delivery = obj.delivery_date
        return delivery.isoformat() if delivery else None


class OrderDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed order view"""

    items = OrderItemSerializer(many=True, read_only=True)
    delivery_date = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'status',
            'customer_name',
            'customer_phone',
            'delivery_address',
            'delivery_city',
            'delivery_state',
            'delivery_postal_code',
            'delivery_country',
            'delivery_notes',
            'subtotal',
            'shipping_cost',
            'tax',
            'total_amount',
            'currency',
            'order_date',
            'confirmed_date',
            'shipped_date',
            'delivered_date',
            'delivery_date',
            'payment_method',
            'payment_status',
            'card_type',
            'card_last_four',
            'items',
        ]

    def get_delivery_date(self, obj):
        delivery = obj.delivery_date
        return delivery.isoformat() if delivery else None


# Authentication Serializers
class SendVerificationSerializer(serializers.Serializer):
    """Serializer for sending verification code"""
    phone = serializers.CharField(max_length=20)
    
    def validate_phone(self, value):
        # Basic phone validation
        import re
        # Remove any non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', value)
        
        if not cleaned.startswith('+'):
            raise serializers.ValidationError("Phone number must start with country code (e.g., +996 or +1)")
        
        if len(cleaned) < 10:
            raise serializers.ValidationError("Phone number is too short")
        
        return cleaned


class VerifyCodeSerializer(serializers.Serializer):
    """Serializer for verifying SMS code"""
    phone = serializers.CharField(max_length=20)
    verification_code = serializers.CharField(max_length=6, min_length=6)
    
    def validate_verification_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Verification code must contain only digits")
        return value


class SuccessMessageSerializer(serializers.Serializer):
    """Generic success response with message."""

    success = serializers.BooleanField()
    message = serializers.CharField()


class AddressListResponseSerializer(serializers.Serializer):
    """Response serializer for address list endpoint."""

    success = serializers.BooleanField()
    addresses = AddressSerializer(many=True)
    total = serializers.IntegerField()


class AddressDetailResponseSerializer(serializers.Serializer):
    """Response serializer for address create/update endpoints."""

    success = serializers.BooleanField()
    message = serializers.CharField()
    address = AddressSerializer()


class PaymentMethodListResponseSerializer(serializers.Serializer):
    """Response serializer for payment method list."""

    success = serializers.BooleanField()
    payment_methods = PaymentMethodSerializer(many=True)
    total = serializers.IntegerField()


class PaymentMethodDetailResponseSerializer(serializers.Serializer):
    """Response serializer for payment method create."""

    success = serializers.BooleanField()
    message = serializers.CharField()
    payment_method = PaymentMethodSerializer()


class PaymentMethodUpdateSerializer(serializers.Serializer):
    """Serializer for updating payment method fields."""

    is_default = serializers.BooleanField()


class OrderListResponseSerializer(serializers.Serializer):
    """Response serializer for orders list."""

    success = serializers.BooleanField()
    orders = OrderListSerializer(many=True)
    total = serializers.IntegerField()
    has_more = serializers.BooleanField()


class OrderDetailResponseSerializer(serializers.Serializer):
    """Response serializer for order detail."""

    success = serializers.BooleanField()
    order = OrderDetailSerializer()


class OrderCancelResponseSerializer(serializers.Serializer):
    """Response serializer for cancelling an order."""

    success = serializers.BooleanField()
    message = serializers.CharField()
    order_id = serializers.IntegerField()
    status = serializers.CharField()


class NotificationListResponseSerializer(serializers.Serializer):
    """Response serializer for notifications list."""

    success = serializers.BooleanField()
    notifications = NotificationSerializer(many=True)
    total = serializers.IntegerField()
    unread_count = serializers.IntegerField()


class NotificationBulkUpdateResponseSerializer(serializers.Serializer):
    """Response serializer for notification read/read-all actions."""

    success = serializers.BooleanField()
    message = serializers.CharField()
    count = serializers.IntegerField(required=False)


class PhoneNumberListResponseSerializer(serializers.Serializer):
    """Response serializer for phone number list."""

    success = serializers.BooleanField()
    phone_numbers = PhoneNumberSerializer(many=True)
    total = serializers.IntegerField()


class PhoneNumberDetailResponseSerializer(serializers.Serializer):
    """Response serializer for phone number create/update."""

    success = serializers.BooleanField()
    message = serializers.CharField()
    phone_number = PhoneNumberSerializer()

