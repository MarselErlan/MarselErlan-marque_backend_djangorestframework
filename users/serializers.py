"""
Serializers for Users App
Handles serialization/deserialization of User, Address, PaymentMethod, Notification models
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Address, PaymentMethod, VerificationCode, Notification

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    formatted_phone = serializers.CharField(source='get_formatted_phone', read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    currency = serializers.CharField(source='get_currency', read_only=True)
    currency_code = serializers.CharField(source='get_currency_code', read_only=True)
    country = serializers.CharField(source='get_country', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'phone', 'formatted_phone', 'name', 'full_name',
            'profile_image_url', 'is_active', 'is_verified',
            'market', 'language', 'country', 'currency', 'currency_code',
            'last_login', 'created_at'
        ]
        read_only_fields = ['id', 'is_verified', 'created_at', 'last_login']


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile"""
    
    class Meta:
        model = User
        fields = ['full_name', 'profile_image_url']
        
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
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        # Auto-set market from user
        user = self.context['request'].user
        validated_data['user'] = user
        validated_data['market'] = user.market
        
        # If this is set as default, unset other defaults
        if validated_data.get('is_default', False):
            Address.objects.filter(user=user, is_default=True).update(is_default=False)
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        # If this is being set as default, unset other defaults
        if validated_data.get('is_default', False) and not instance.is_default:
            Address.objects.filter(user=instance.user, is_default=True).update(is_default=False)
        
        return super().update(instance, validated_data)


class AddressCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating addresses (no user field required)"""
    
    class Meta:
        model = Address
        fields = [
            'title', 'full_address', 'street', 'building', 'apartment',
            'city', 'state', 'postal_code', 'country', 'is_default'
        ]


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
        validated_data['market'] = user.market
        
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


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model"""
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'type', 'title', 'message', 'is_read',
            'order_id', 'market', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']


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

