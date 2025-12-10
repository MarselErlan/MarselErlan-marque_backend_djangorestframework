"""
Admin configuration for Stores app.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.contrib import messages
from .models import Store, StoreFollower


# StoreAdmin is now in admin_store_owner.py for store owners
# Superusers can still use this, but store owners will use StoreOwnerStoreAdmin
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
                # request is the HttpRequest object, request.user is the user
                obj.owner = request.user
            # Set default status to pending for new stores
            if not obj.status:
                obj.status = 'pending'
        super().save_model(request, obj, form, change)
    
    # Admin Actions
    @admin.action(description='Approve selected stores')
    def approve_stores(self, request, queryset):
        """Approve selected stores (set status to active)."""
        updated = queryset.update(status='active', is_active=True)
        self.message_user(
            request,
            f'{updated} store(s) approved and activated.',
        )
    approve_stores.short_description = 'Approve selected stores'
    
    @admin.action(description='Suspend selected stores')
    def suspend_stores(self, request, queryset):
        """Suspend selected stores (set status to suspended and deactivate)."""
        updated = queryset.update(status='suspended', is_active=False)
        self.message_user(
            request,
            f'{updated} store(s) suspended and deactivated.',
        )
    suspend_stores.short_description = 'Suspend selected stores'
    
    @admin.action(description='Verify selected stores')
    def verify_stores(self, request, queryset):
        """Verify selected stores (add verified badge)."""
        updated = queryset.update(is_verified=True)
        self.message_user(
            request,
            f'{updated} store(s) verified.',
        )
    verify_stores.short_description = 'Verify selected stores'
    
    @admin.action(description='Feature selected stores')
    def feature_stores(self, request, queryset):
        """Feature selected stores (show prominently)."""
        updated = queryset.update(is_featured=True)
        self.message_user(
            request,
            f'{updated} store(s) featured.',
        )
    feature_stores.short_description = 'Feature selected stores'
    
    @admin.action(description='Unfeature selected stores')
    def unfeature_stores(self, request, queryset):
        """Remove featured status from selected stores."""
        updated = queryset.update(is_featured=False)
        self.message_user(
            request,
            f'{updated} store(s) unfeatured.',
        )
    unfeature_stores.short_description = 'Unfeature selected stores'
    
    actions = [
        approve_stores,
        suspend_stores,
        verify_stores,
        feature_stores,
        unfeature_stores,
    ]


@admin.register(StoreFollower)
class StoreFollowerAdmin(admin.ModelAdmin):
    """Admin interface for StoreFollower model."""
    
    list_display = ['user', 'store', 'created_at']
    list_filter = ['created_at', 'store']
    search_fields = ['user__phone', 'user__full_name', 'store__name']
    readonly_fields = ['created_at']
