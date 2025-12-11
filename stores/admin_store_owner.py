"""
Django Admin configuration for Store Owners.
Store owners can only see and manage their own stores.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from .models import Store, StoreFollower


class StoreOwnerStoreAdmin(admin.ModelAdmin):
    """
    Custom admin for store owners - they can only manage their own stores.
    This admin automatically filters stores by owner and adapts based on user type.
    """
    
    def has_module_permission(self, request):
        """Allow store owners to see the Stores module only if they have stores"""
        if request.user.is_superuser:
            return True
        # Store owners can only see Stores module if they have at least one active store
        # If no stores, hide the module completely
        if not request.user.is_staff:
            return False
        return request.user.owned_stores.filter(is_active=True).exists()
    
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
        'rating', 'reviews_count', 'orders_count', 'products_count',
        'likes_count', 'created_at', 'updated_at'
    ]
    # Note: prepopulated_fields only works when field is editable
    # We'll handle slug readonly state dynamically in get_readonly_fields
    prepopulated_fields = {'slug': ('name',)}
    
    # Admin Actions (for superusers only)
    @admin.action(description='Approve selected stores')
    def approve_stores(self, request, queryset):
        """Approve selected stores (set status to active)."""
        if not request.user.is_superuser:
            return
        updated = queryset.update(status='active', is_active=True)
        self.message_user(
            request,
            f'{updated} store(s) approved and activated.',
        )
    
    @admin.action(description='Suspend selected stores')
    def suspend_stores(self, request, queryset):
        """Suspend selected stores (set status to suspended and deactivate)."""
        if not request.user.is_superuser:
            return
        updated = queryset.update(status='suspended', is_active=False)
        self.message_user(
            request,
            f'{updated} store(s) suspended and deactivated.',
        )
    
    @admin.action(description='Verify selected stores')
    def verify_stores(self, request, queryset):
        """Verify selected stores."""
        if not request.user.is_superuser:
            return
        updated = queryset.update(is_verified=True)
        self.message_user(
            request,
            f'{updated} store(s) verified.',
        )
    
    @admin.action(description='Feature selected stores')
    def feature_stores(self, request, queryset):
        """Feature selected stores."""
        if not request.user.is_superuser:
            return
        updated = queryset.update(is_featured=True)
        self.message_user(
            request,
            f'{updated} store(s) featured.',
        )
    
    @admin.action(description='Unfeature selected stores')
    def unfeature_stores(self, request, queryset):
        """Unfeature selected stores."""
        if not request.user.is_superuser:
            return
        updated = queryset.update(is_featured=False)
        self.message_user(
            request,
            f'{updated} store(s) unfeatured.',
        )
    
    actions = [
        'approve_stores',
        'suspend_stores',
        'verify_stores',
        'feature_stores',
        'unfeature_stores',
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'owner', 'market'),
            'description': 'Slug is auto-generated from name when creating. It becomes readonly after creation.'
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
    
    def get_queryset(self, request):
        """
        Filter stores to show only those owned by the current user.
        Superusers can see all stores.
        """
        qs = super().get_queryset(request)
        
        if request.user.is_superuser:
            return qs.select_related('owner')
        
        # Store owners can only see their own stores
        return qs.filter(owner=request.user, is_active=True).select_related('owner')
    
    def has_add_permission(self, request):
        """
        Store owners can add stores (they become the owner).
        """
        return True
    
    def has_change_permission(self, request, obj=None):
        """
        Store owners can only change their own stores.
        """
        if request.user.is_superuser:
            return True
        
        if obj is not None:
            return obj.owner == request.user
        
        return True
    
    def has_delete_permission(self, request, obj=None):
        """
        Store owners can only delete their own stores.
        """
        if request.user.is_superuser:
            return True
        
        if obj is not None:
            return obj.owner == request.user
        
        return True
    
    def save_model(self, request, obj, form, change):
        """
        Auto-set owner if creating new store and owner is not set.
        For store owners, always set owner to current user.
        For superusers, only set if owner is not already set.
        """
        if not change:  # Creating new store
            if not request.user.is_superuser:
                # Store owners: always set to current user
                obj.owner = request.user
            elif not obj.owner_id:
                # Superusers: set to current user if not specified
                obj.owner = request.user
            
            if not obj.status:
                obj.status = 'pending'
        
        super().save_model(request, obj, form, change)
    
    def get_readonly_fields(self, request, obj=None):
        """
        Make owner and slug readonly if editing existing store.
        Slug is editable when creating (for prepopulated_fields to work).
        """
        readonly = list(self.readonly_fields)
        
        if obj:  # Editing existing store
            readonly.append('owner')
            readonly.append('slug')  # Make slug readonly when editing
        
        return readonly
    
    def get_form(self, request, obj=None, **kwargs):
        """
        Safely handle form fields, especially owner field for store owners.
        """
        form = super().get_form(request, obj, **kwargs)
        
        if not request.user.is_superuser:
            # For store owners, ensure owner field is handled correctly
            # Owner is auto-set in save_model, but we can filter the queryset if needed
            if 'owner' in form.base_fields:
                # For store owners, limit owner choices to themselves
                # (though owner is auto-set, this prevents confusion)
                from django.contrib.auth import get_user_model
                User = get_user_model()
                form.base_fields['owner'].queryset = User.objects.filter(id=request.user.id)
        
        return form
    
    def get_prepopulated_fields(self, request, obj=None):
        """
        Only enable prepopulated_fields when creating (not editing).
        This prevents KeyError when slug is readonly.
        """
        if obj is None:  # Creating new store
            return self.prepopulated_fields
        return {}  # Disable prepopulated_fields when editing

