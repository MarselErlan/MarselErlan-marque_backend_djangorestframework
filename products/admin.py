from django.contrib import admin
from .models import (Category, Subcategory, Product, ProductImage, 
                     ProductFeature, ProductSizeOption, ProductColorOption, SKU,
                     Cart, CartItem, Wishlist, WishlistItem)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'market', 'slug', 'is_active', 'sort_order', 'created_at')
    list_filter = ('market', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('market', 'sort_order', 'name')


@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'slug', 'is_active', 'sort_order', 'created_at')
    list_filter = ('category', 'is_active', 'created_at')
    search_fields = ('name', 'description', 'category__name')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('category', 'sort_order', 'name')


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'alt_text', 'sort_order')


class ProductFeatureInline(admin.TabularInline):
    model = ProductFeature
    extra = 1
    fields = ('feature_text', 'sort_order')


class ProductSizeOptionInline(admin.TabularInline):
    model = ProductSizeOption
    extra = 1
    fields = ('name', 'sort_order', 'is_active')


class ProductColorOptionInline(admin.TabularInline):
    model = ProductColorOption
    fk_name = 'product'
    extra = 1
    fields = ('size', 'name', 'hex_code', 'is_active')

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'size' and request is not None:
            obj_id = request.resolver_match.kwargs.get('object_id')
            if obj_id:
                kwargs['queryset'] = ProductSizeOption.objects.filter(product_id=obj_id)
            else:
                kwargs['queryset'] = ProductSizeOption.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class SKUInline(admin.TabularInline):
    model = SKU
    extra = 1
    fields = ('sku_code', 'size_option', 'color_option', 'price', 'original_price', 'stock', 'variant_image', 'is_active')
    readonly_fields = ('sku_code',)

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if request is not None:
            obj_id = request.resolver_match.kwargs.get('object_id')
            if obj_id:
                if db_field.name == 'size_option':
                    kwargs['queryset'] = ProductSizeOption.objects.filter(product_id=obj_id)
                if db_field.name == 'color_option':
                    kwargs['queryset'] = ProductColorOption.objects.filter(product_id=obj_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'market', 'gender', 'category', 'subcategory', 'price', 'discount', 'sales_count', 'rating', 'in_stock', 'is_active')
    list_filter = ('market', 'gender', 'category', 'subcategory', 'brand', 'is_active', 'in_stock', 'is_featured', 'is_best_seller', 'created_at')
    search_fields = ('name', 'brand', 'description', 'ai_description')
    prepopulated_fields = {'slug': ('brand', 'name')}
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    
    inlines = [ProductSizeOptionInline, ProductColorOptionInline, SKUInline, ProductImageInline, ProductFeatureInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'brand', 'description', 'market', 'gender')
        }),
        ('AI-Enhanced Information', {
            'fields': ('ai_description', 'style_tags', 'occasion_tags', 'season_tags', 'color_tags', 'material_tags', 'age_group_tags', 'activity_tags'),
            'classes': ('collapse',),
            'description': 'These fields help AI understand and recommend products better'
        }),
        ('Categorization', {
            'fields': ('category', 'subcategory')
        }),
        ('Pricing', {
            'fields': ('price', 'original_price', 'discount')
        }),
        ('Images', {
            'fields': ('image',)
        }),
        ('Ratings & Reviews', {
            'fields': ('rating', 'reviews_count')
        }),
        ('Sales & Stock', {
            'fields': ('sales_count', 'in_stock')
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured', 'is_best_seller')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SKU)
class SKUAdmin(admin.ModelAdmin):
    list_display = ('sku_code', 'product', 'size_option', 'color_option', 'price', 'stock', 'is_active')
    list_filter = ('is_active', 'size_option__name', 'color_option__name', 'created_at')
    search_fields = ('sku_code', 'product__name', 'product__brand')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ProductSizeOption)
class ProductSizeOptionAdmin(admin.ModelAdmin):
    list_display = ('product', 'name', 'sort_order', 'is_active')
    list_filter = ('is_active', 'product')
    search_fields = ('product__name', 'name')
    ordering = ('product', 'sort_order', 'name')


@admin.register(ProductColorOption)
class ProductColorOptionAdmin(admin.ModelAdmin):
    list_display = ('product', 'size', 'name', 'is_active')
    list_filter = ('is_active', 'product', 'size')
    search_fields = ('product__name', 'size__name', 'name')
    ordering = ('product', 'size__name', 'name')


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    fields = ('sku', 'quantity', 'subtotal')
    readonly_fields = ('subtotal',)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_items', 'total_price', 'updated_at')
    search_fields = ('user__phone', 'user__full_name')
    ordering = ('-updated_at',)
    readonly_fields = ('created_at', 'updated_at', 'total_items', 'total_price')
    inlines = [CartItemInline]


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'sku', 'quantity', 'subtotal', 'updated_at')
    search_fields = ('cart__user__phone', 'sku__product__name')
    ordering = ('-updated_at',)
    readonly_fields = ('created_at', 'updated_at', 'subtotal')


class WishlistItemInline(admin.TabularInline):
    model = WishlistItem
    extra = 0
    fields = ('product', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'updated_at')
    search_fields = ('user__phone', 'user__full_name')
    ordering = ('-updated_at',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [WishlistItemInline]


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ('wishlist', 'product', 'created_at')
    search_fields = ('wishlist__user__phone', 'product__name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
