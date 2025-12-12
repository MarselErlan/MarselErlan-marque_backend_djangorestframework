"""
Serializers for Stores app.
"""

from rest_framework import serializers
from django.utils.text import slugify
from .models import Store, StoreFollower
from products.models import Product, Category, Subcategory, Brand, Currency


class StoreListSerializer(serializers.ModelSerializer):
    """Serializer for listing stores."""
    
    logo_url = serializers.SerializerMethodField()
    cover_image_url = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    
    class Meta:
        model = Store
        fields = [
            'id', 'name', 'slug', 'logo', 'logo_url', 'cover_image', 'cover_image_url',
            'rating', 'reviews_count', 'orders_count', 'products_count', 'likes_count',
            'is_verified', 'is_featured', 'market', 'is_following',
        ]
        read_only_fields = [
            'id', 'slug', 'rating', 'reviews_count', 'orders_count',
            'products_count', 'likes_count',
        ]
    
    def get_logo_url(self, obj):
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
            return obj.logo.url
        return obj.logo_url
    
    def get_cover_image_url(self, obj):
        if obj.cover_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.cover_image.url)
            return obj.cover_image.url
        return obj.cover_image_url
    
    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            return StoreFollower.objects.filter(user=request.user, store=obj).exists()
        return False


class StoreDetailSerializer(serializers.ModelSerializer):
    """Serializer for store detail view."""
    
    logo_url = serializers.SerializerMethodField()
    cover_image_url = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Store
        fields = [
            'id', 'name', 'slug', 'description', 'logo', 'logo_url', 'cover_image',
            'cover_image_url', 'email', 'phone', 'website', 'address', 'rating',
            'reviews_count', 'orders_count', 'products_count', 'likes_count',
            'is_verified', 'is_featured', 'status', 'market', 'owner', 'owner_name',
            'is_following', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'slug', 'rating', 'reviews_count', 'orders_count',
            'products_count', 'likes_count', 'created_at', 'updated_at',
        ]
    
    def get_logo_url(self, obj):
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
            return obj.logo.url
        return obj.logo_url
    
    def get_cover_image_url(self, obj):
        if obj.cover_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.cover_image.url)
            return obj.cover_image.url
        return obj.cover_image_url
    
    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            return StoreFollower.objects.filter(user=request.user, store=obj).exists()
        return False
    
    def get_owner_name(self, obj):
        return obj.owner.full_name if obj.owner else None


class StoreRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for store registration."""
    
    class Meta:
        model = Store
        fields = ['name', 'description', 'market', 'email', 'phone', 'website', 'address']
    
    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        validated_data['status'] = 'pending'
        validated_data['is_active'] = False
        store = Store.objects.create(**validated_data)
        
        # Grant staff access to store owner so they can access Django admin
        # This allows them to manage their store and products through admin interface
        owner = validated_data['owner']
        if not owner.is_staff:
            owner.is_staff = True
            owner.save(update_fields=['is_staff'])
        
        return store
    
    def validate_name(self, value):
        if Store.objects.filter(name=value).exists():
            raise serializers.ValidationError("A store with this name already exists.")
        return value


class StoreUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating store information."""
    
    class Meta:
        model = Store
        fields = [
            'name', 'description', 'email', 'phone', 'website', 'address',
            'logo_url', 'cover_image_url', 'is_active', 'is_featured', 'market'
        ]
        read_only_fields = ['market']
    
    def validate_name(self, value):
        instance = self.instance
        if instance and instance.name == value:
            return value
        if Store.objects.filter(name=value).exists():
            raise serializers.ValidationError("A store with this name already exists.")
        return value


class StoreAdminProductSerializer(serializers.ModelSerializer):
    """Serializer for store owners to create/update products."""
    
    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'slug',
            'description',
            'category',
            'subcategory',
            'second_subcategory',
            'brand',
            'store',
            'price',
            'original_price',
            'discount',
            'currency',
            'market',
            'gender',
            'in_stock',
            'is_active',
            'is_featured',
            'is_best_seller',
            'ai_description',
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']
    
    def validate_store(self, value):
        """Ensure user owns the store"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            if not request.user.is_superuser and value.owner != request.user:
                raise serializers.ValidationError("You can only create products for your own stores.")
        return value
    
    def validate(self, data):
        """Validate product data"""
        # Ensure subcategory belongs to category
        if data.get('subcategory') and data.get('category'):
            if data['subcategory'].category != data['category']:
                raise serializers.ValidationError({
                    'subcategory': 'Subcategory must belong to the selected category.'
                })
        
        # Ensure second_subcategory belongs to subcategory
        if data.get('second_subcategory') and data.get('subcategory'):
            if data['second_subcategory'].parent_subcategory != data['subcategory']:
                raise serializers.ValidationError({
                    'second_subcategory': 'Second subcategory must be a child of the first subcategory.'
                })
        
        return data
