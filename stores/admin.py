"""
Admin configuration for Stores app.
"""

from django.contrib import admin
from .models import Store, StoreFollower


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    """Admin interface for Store model."""
    
    list_display = [
        'name',
        'slug',
        'owner',
        'market',
        'status',
        'is_active',
        'is_verified',
        'is_featured',
        'rating',
        'products_count',
        'orders_count',
        'created_at',
    ]
    list_filter = [
        'market',
        'status',
        'is_active',
        'is_verified',
        'is_featured',
        'created_at',
    ]
    search_fields = ['name', 'slug', 'owner__phone', 'owner__full_name', 'email']
    readonly_fields = [
        'slug',
        'rating',
        'reviews_count',
        'orders_count',
        'products_count',
        'likes_count',
        'created_at',
        'updated_at',
    ]
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'owner', 'market')
        }),
        ('Visual Identity', {
            'fields': ('logo', 'logo_url', 'cover_image', 'cover_image_url')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone', 'website', 'address')
        }),
        ('Statistics', {
            'fields': (
                'rating',
                'reviews_count',
                'orders_count',
                'products_count',
                'likes_count',
            )
        }),
        ('Status', {
            'fields': ('status', 'is_active', 'is_verified', 'is_featured')
        }),
        ('Contract', {
            'fields': ('contract_signed_date', 'contract_expiry_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Auto-set owner if creating new store."""
        if not change:  # Creating new store
            if not obj.owner_id:
                obj.owner = request.user
        super().save_model(request, obj, form, change)


@admin.register(StoreFollower)
class StoreFollowerAdmin(admin.ModelAdmin):
    """Admin interface for StoreFollower model."""
    
    list_display = ['user', 'store', 'created_at']
    list_filter = ['created_at', 'store']
    search_fields = ['user__phone', 'user__full_name', 'store__name']
    readonly_fields = ['created_at']
