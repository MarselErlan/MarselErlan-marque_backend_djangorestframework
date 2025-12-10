"""
Serializers for Referral Fee app.
"""

from rest_framework import serializers
from .models import ReferralFee


class ReferralFeeSerializer(serializers.ModelSerializer):
    """Serializer for ReferralFee model."""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True, allow_null=True)
    subcategory_slug = serializers.CharField(source='subcategory.slug', read_only=True, allow_null=True)
    second_subcategory_name = serializers.CharField(source='second_subcategory.name', read_only=True, allow_null=True)
    second_subcategory_slug = serializers.CharField(source='second_subcategory.slug', read_only=True, allow_null=True)
    
    class Meta:
        model = ReferralFee
        fields = [
            'id',
            'category',
            'category_name',
            'category_slug',
            'subcategory',
            'subcategory_name',
            'subcategory_slug',
            'second_subcategory',
            'second_subcategory_name',
            'second_subcategory_slug',
            'fee_percentage',
            'fee_fixed',
            'is_active',
            'description',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validate fee configuration"""
        # If second_subcategory is set, subcategory must also be set
        if data.get('second_subcategory') and not data.get('subcategory'):
            raise serializers.ValidationError({
                'second_subcategory': 'Cannot set second_subcategory without first-level subcategory.'
            })
        
        # If second_subcategory is set, it must be a child of subcategory
        if data.get('second_subcategory') and data.get('subcategory'):
            if data['second_subcategory'].parent_subcategory != data['subcategory']:
                raise serializers.ValidationError({
                    'second_subcategory': 'Second subcategory must be a child of the first subcategory.'
                })
        
        # Ensure all subcategories belong to the same category
        category = data.get('category')
        if category:
            if data.get('subcategory') and data['subcategory'].category != category:
                raise serializers.ValidationError({
                    'subcategory': 'Subcategory must belong to the same category.'
                })
            
            if data.get('second_subcategory') and data['second_subcategory'].category != category:
                raise serializers.ValidationError({
                    'second_subcategory': 'Second subcategory must belong to the same category.'
                })
            
            # Ensure subcategory is first-level (no parent)
            if data.get('subcategory') and data['subcategory'].parent_subcategory:
                raise serializers.ValidationError({
                    'subcategory': 'Subcategory must be a first-level subcategory (no parent).'
                })
        
        return data


class ReferralFeeListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing referral fees."""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True, allow_null=True)
    second_subcategory_name = serializers.CharField(source='second_subcategory.name', read_only=True, allow_null=True)
    
    class Meta:
        model = ReferralFee
        fields = [
            'id',
            'category',
            'category_name',
            'subcategory',
            'subcategory_name',
            'second_subcategory',
            'second_subcategory_name',
            'fee_percentage',
            'fee_fixed',
            'is_active',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class CalculateFeeSerializer(serializers.Serializer):
    """Serializer for calculating fee for a product."""
    
    product_id = serializers.IntegerField(required=True)
    order_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    
    def validate_order_amount(self, value):
        """Validate order amount is positive"""
        if value <= 0:
            raise serializers.ValidationError("Order amount must be positive.")
        return value

