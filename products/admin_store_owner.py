"""
Django Admin configuration for Store Owners.
Store owners can only see and manage products from their own stores.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from .models import Product, SKU, ProductImage, ProductFeature, ProductSizeOption, ProductColorOption


class StoreOwnerProductAdmin(admin.ModelAdmin):
    """
    Custom admin for store owners - they can only manage products from their own stores.
    """
    
    def has_module_permission(self, request):
        """Allow store owners to see the Products module in admin"""
        if request.user.is_superuser:
            return True
        # Store owners with active stores can see this module
        return request.user.is_staff and request.user.owned_stores.filter(is_active=True).exists()
    
    list_display = (
        'name', 'brand', 'store', 'category', 'subcategory', 'second_subcategory',
        'price', 'in_stock', 'is_active', 'created_at'
    )
    list_filter = ('is_active', 'in_stock', 'category', 'brand', 'created_at')
    search_fields = ('name', 'description', 'brand__name', 'store__name')
    readonly_fields = ('created_at', 'updated_at', 'rating', 'reviews_count', 'sales_count')
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'store', 'brand')
        }),
        ('Category Structure', {
            'fields': ('category', 'subcategory', 'second_subcategory'),
            'description': 'Select category hierarchy for this product'
        }),
        ('Pricing', {
            'fields': ('price', 'original_price', 'discount', 'currency')
        }),
        ('Product Details', {
            'fields': ('market', 'gender', 'ai_description')
        }),
        ('Status', {
            'fields': ('is_active', 'in_stock', 'is_featured', 'is_best_seller')
        }),
        ('Statistics (Read-only)', {
            'fields': ('rating', 'reviews_count', 'sales_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """
        Filter products to show only those from stores owned by the current user.
        Superusers can see all products.
        """
        qs = super().get_queryset(request)
        
        # Superusers can see everything
        if request.user.is_superuser:
            return qs.select_related('category', 'subcategory', 'second_subcategory', 'brand', 'store', 'currency')
        
        # Store owners can only see products from their stores
        user_stores = request.user.owned_stores.filter(is_active=True)
        if not user_stores.exists():
            # User has no stores, return empty queryset
            return qs.none()
        
        return qs.filter(store__in=user_stores).select_related(
            'category', 'subcategory', 'second_subcategory', 'brand', 'store', 'currency'
        )
    
    def get_readonly_fields(self, request, obj=None):
        """
        Make store field readonly for store owners (they can't change store ownership).
        Superusers can change store.
        """
        readonly = list(self.readonly_fields)
        
        if not request.user.is_superuser:
            # Store owners cannot change the store field
            readonly.append('store')
        
        return readonly
    
    def has_change_permission(self, request, obj=None):
        """
        Store owners can only change products from their own stores.
        """
        if request.user.is_superuser:
            return True
        
        if obj is not None:
            # Check if product belongs to user's store
            return obj.store.owner == request.user
        
        return True  # Allow access to list view
    
    def has_delete_permission(self, request, obj=None):
        """
        Store owners can only delete products from their own stores.
        """
        if request.user.is_superuser:
            return True
        
        if obj is not None:
            # Check if product belongs to user's store
            return obj.store.owner == request.user
        
        return True  # Allow access to list view
    
    def save_model(self, request, obj, form, change):
        """
        Auto-assign store if creating new product and user is not superuser.
        """
        if not change and not request.user.is_superuser:
            # If creating new product and user is store owner, assign to their first store
            user_stores = request.user.owned_stores.filter(is_active=True)
            if user_stores.exists():
                obj.store = user_stores.first()
            else:
                raise PermissionDenied("You must own at least one active store to create products.")
        
        super().save_model(request, obj, form, change)
    
    def get_form(self, request, obj=None, **kwargs):
        """
        Filter store dropdown to show only user's stores.
        """
        form = super().get_form(request, obj, **kwargs)
        
        if not request.user.is_superuser:
            # Limit store choices to user's stores
            user_stores = request.user.owned_stores.filter(is_active=True)
            form.base_fields['store'].queryset = user_stores
            
            # If editing existing product, ensure it's from user's store
            if obj and obj.store not in user_stores:
                raise PermissionDenied("You don't have permission to edit this product.")
        
        return form


class StoreOwnerSKUAdmin(admin.ModelAdmin):
    """
    Custom admin for SKUs - store owners can only manage SKUs from their products.
    """
    
    list_display = ('product', 'sku_code', 'size', 'color', 'price', 'stock', 'is_active')
    list_filter = ('is_active', 'product__store')
    search_fields = ('sku_code', 'product__name')
    readonly_fields = ('created_at', 'updated_at')
    
    def get_queryset(self, request):
        """
        Filter SKUs to show only those from products owned by the user's stores.
        """
        qs = super().get_queryset(request)
        
        if request.user.is_superuser:
            return qs.select_related('product', 'product__store', 'size_option', 'color_option')
        
        user_stores = request.user.owned_stores.filter(is_active=True)
        if not user_stores.exists():
            return qs.none()
        
        return qs.filter(product__store__in=user_stores).select_related(
            'product', 'product__store', 'size_option', 'color_option'
        )
    
    def get_form(self, request, obj=None, **kwargs):
        """
        Filter product dropdown to show only user's products.
        """
        form = super().get_form(request, obj, **kwargs)
        
        if not request.user.is_superuser:
            user_stores = request.user.owned_stores.filter(is_active=True)
            user_products = Product.objects.filter(store__in=user_stores)
            form.base_fields['product'].queryset = user_products
        
        return form


class StoreOwnerProductImageAdmin(admin.ModelAdmin):
    """
    Custom admin for product images - store owners can only manage images from their products.
    """
    
    list_display = ('product', 'image', 'alt_text', 'sort_order')
    list_filter = ('product__store',)
    search_fields = ('product__name', 'alt_text')
    
    def get_queryset(self, request):
        """
        Filter images to show only those from products owned by the user's stores.
        """
        qs = super().get_queryset(request)
        
        if request.user.is_superuser:
            return qs.select_related('product', 'product__store')
        
        user_stores = request.user.owned_stores.filter(is_active=True)
        if not user_stores.exists():
            return qs.none()
        
        return qs.filter(product__store__in=user_stores).select_related('product', 'product__store')
    
    def get_form(self, request, obj=None, **kwargs):
        """
        Filter product dropdown to show only user's products.
        """
        form = super().get_form(request, obj, **kwargs)
        
        if not request.user.is_superuser:
            user_stores = request.user.owned_stores.filter(is_active=True)
            user_products = Product.objects.filter(store__in=user_stores)
            form.base_fields['product'].queryset = user_products
        
        return form


class StoreOwnerProductFeatureAdmin(admin.ModelAdmin):
    """
    Custom admin for product features - store owners can only manage features from their products.
    """
    
    list_display = ('product', 'feature_text')
    list_filter = ('product__store',)
    search_fields = ('product__name', 'feature_text')
    
    def get_queryset(self, request):
        """
        Filter features to show only those from products owned by the user's stores.
        """
        qs = super().get_queryset(request)
        
        if request.user.is_superuser:
            return qs.select_related('product', 'product__store')
        
        user_stores = request.user.owned_stores.filter(is_active=True)
        if not user_stores.exists():
            return qs.none()
        
        return qs.filter(product__store__in=user_stores).select_related('product', 'product__store')
    
    def get_form(self, request, obj=None, **kwargs):
        """
        Filter product dropdown to show only user's products.
        """
        form = super().get_form(request, obj, **kwargs)
        
        if not request.user.is_superuser:
            user_stores = request.user.owned_stores.filter(is_active=True)
            user_products = Product.objects.filter(store__in=user_stores)
            form.base_fields['product'].queryset = user_products
        
        return form

