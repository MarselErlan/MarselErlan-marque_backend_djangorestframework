"""
Serializers for Stores app.
"""

from rest_framework import serializers
from .models import Store, StoreFollower


class StoreListSerializer(serializers.ModelSerializer):
    """Serializer for store list view - minimal data."""
    
    logo_url = serializers.SerializerMethodField()
    cover_image_url = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    
    class Meta:
        model = Store
        fields = [
            'id',
            'name',
            'slug',
            'logo',
            'logo_url',
            'cover_image',
            'cover_image_url',
            'rating',
            'reviews_count',
            'orders_count',
            'products_count',
            'likes_count',
            'is_verified',
            'is_featured',
            'market',
            'is_following',
        ]
        read_only_fields = [
            'id',
            'slug',
            'rating',
            'reviews_count',
            'orders_count',
            'products_count',
            'likes_count',
        ]
    
    def get_logo_url(self, obj):
        """Return logo URL if available."""
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
            return obj.logo.url
        return obj.logo_url
    
    def get_cover_image_url(self, obj):
        """Return cover image URL if available."""
        if obj.cover_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.cover_image.url)
            return obj.cover_image.url
        return obj.cover_image_url
    
    def get_is_following(self, obj):
        """Check if current user is following this store."""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            return StoreFollower.objects.filter(
                user=request.user,
                store=obj
            ).exists()
        return False


class StoreDetailSerializer(serializers.ModelSerializer):
    """Serializer for store detail view - full data."""
    
    logo_url = serializers.SerializerMethodField()
    cover_image_url = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Store
        fields = [
            'id',
            'name',
            'slug',
            'description',
            'logo',
            'logo_url',
            'cover_image',
            'cover_image_url',
            'email',
            'phone',
            'website',
            'address',
            'rating',
            'reviews_count',
            'orders_count',
            'products_count',
            'likes_count',
            'is_verified',
            'is_featured',
            'status',
            'market',
            'owner',
            'owner_name',
            'is_following',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'slug',
            'rating',
            'reviews_count',
            'orders_count',
            'products_count',
            'likes_count',
            'created_at',
            'updated_at',
        ]
    
    def get_logo_url(self, obj):
        """Return logo URL if available."""
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
            return obj.logo.url
        return obj.logo_url
    
    def get_cover_image_url(self, obj):
        """Return cover image URL if available."""
        if obj.cover_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.cover_image.url)
            return obj.cover_image.url
        return obj.cover_image_url
    
    def get_is_following(self, obj):
        """Check if current user is following this store."""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            return StoreFollower.objects.filter(
                user=request.user,
                store=obj
            ).exists()
        return False
    
    def get_owner_name(self, obj):
        """Get owner's full name."""
        return obj.owner.full_name if obj.owner else None

