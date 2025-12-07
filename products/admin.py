from django.contrib import admin
from .models import (Brand, Category, Subcategory, Product, ProductImage, 
                     ProductFeature, ProductSizeOption, ProductColorOption, SKU,
                     Cart, CartItem, Wishlist, WishlistItem, Currency)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'image', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'symbol', 'exchange_rate', 'is_base', 'market', 'is_active', 'updated_at')
    list_filter = ('is_active', 'is_base', 'market', 'market')
    search_fields = ('code', 'name', 'symbol')
    ordering = ('code',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'symbol', 'market')
        }),
        ('Exchange Rate', {
            'fields': ('exchange_rate', 'is_base'),
            'description': 'Exchange rate relative to base currency (USD). Base currency must have rate = 1.0'
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'market', 'slug', 'is_active', 'sort_order', 'product_count_display', 'subcategory_count_display', 'created_at')
    list_filter = ('market', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('market', 'sort_order', 'name')
    readonly_fields = ('created_at', 'updated_at', 'product_count_display', 'subcategory_count_display')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'market', 'description')
        }),
        ('Images', {
            'fields': ('image', 'image_url', 'icon'),
            'description': 'Upload image/icon files OR provide an external image URL. Uploaded files take priority. Icon is for category icon/image upload.'
        }),
        ('Settings', {
            'fields': ('is_active', 'sort_order')
        }),
        ('Statistics', {
            'fields': ('product_count_display', 'subcategory_count_display'),
            'classes': ('collapse',),
            'description': 'Product count: Products directly assigned to this category (level 1).\n'
                          'Subcategory count: Number of first-level subcategories.\n\n'
                          'Rule: Cannot create subcategories if category has products. '
                          'Cannot add products if category has subcategories.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def product_count_display(self, obj):
        """Display count of products directly assigned to category (level 1)"""
        if obj.pk:
            count = Product.objects.filter(
                category=obj,
                subcategory__isnull=True
            ).count()
            return count
        return "—"
    product_count_display.short_description = 'Level 1 Products'
    
    def subcategory_count_display(self, obj):
        """Display count of first-level subcategories"""
        if obj.pk:
            count = obj.subcategories.filter(parent_subcategory__isnull=True).count()
            return count if count > 0 else "—"
        return "—"
    subcategory_count_display.short_description = 'Subcategories'


class ChildSubcategoryInline(admin.TabularInline):
    """Inline admin for showing child subcategories"""
    model = Subcategory
    fk_name = 'parent_subcategory'
    extra = 0
    fields = ('name', 'slug', 'is_active', 'sort_order', 'product_count_display')
    readonly_fields = ('product_count_display',)
    can_delete = True
    show_change_link = True
    
    def product_count_display(self, obj):
        """Display product count for child subcategory"""
        if obj.pk:
            count = obj.second_level_products.count()
            return count
        return "—"
    product_count_display.short_description = 'Products'


@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'parent_subcategory', 'level_display', 'slug', 'is_active', 'sort_order', 'product_count_display', 'child_count_display', 'created_at')
    list_filter = ('category', 'parent_subcategory', 'is_active', 'created_at')
    search_fields = ('name', 'description', 'category__name', 'parent_subcategory__name')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('category', 'parent_subcategory', 'sort_order', 'name')
    readonly_fields = ('created_at', 'updated_at', 'level_display', 'product_count_display', 'child_count_display')
    inlines = [ChildSubcategoryInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'parent_subcategory', 'name', 'slug', 'description')
        }),
        ('Level Information', {
            'fields': ('level_display',),
            'description': 'Level 1: First-level subcategory (no parent). Level 2: Second-level subcategory (has parent).\n\n'
                          'Validation Rules:\n'
                          '• Cannot create subcategory (level 2) if category has products directly (level 1).\n'
                          '• Cannot create child subcategory (level 3) if parent subcategory (level 2) has products.\n'
                          '• All levels must be unique within their scope.',
            'classes': ('collapse',)
        }),
        ('Images', {
            'fields': ('image', 'image_url'),
            'description': 'Upload image file OR provide an external image URL. Uploaded files take priority.'
        }),
        ('Settings', {
            'fields': ('is_active', 'sort_order')
        }),
        ('Statistics', {
            'fields': ('product_count_display', 'child_count_display'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def level_display(self, obj):
        """Display the level of this subcategory"""
        if obj.pk:
            level = obj.level
            if level == 1:
                return "Level 1 (First-level)"
            elif level == 2:
                return "Level 2 (Second-level)"
            return "Unknown"
        return "—"
    level_display.short_description = 'Level'
    level_display.admin_order_field = 'parent_subcategory'
    
    def product_count_display(self, obj):
        """Display product count for this subcategory"""
        if obj.pk:
            if obj.level == 1:
                # Count products with this subcategory and no second_subcategory
                count = obj.products.filter(second_subcategory__isnull=True).count()
            else:
                # Count products with this as second_subcategory
                count = obj.second_level_products.count()
            return count
        return "—"
    product_count_display.short_description = 'Products'
    
    def child_count_display(self, obj):
        """Display count of child subcategories"""
        if obj.pk and obj.level == 1:
            count = obj.child_subcategories.count()
            return count if count > 0 else "—"
        return "—"
    child_count_display.short_description = 'Child Subcategories'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('category', 'parent_subcategory')
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter category and parent_subcategory based on validation rules"""
        obj_id = request.resolver_match.kwargs.get('object_id')
        
        # Filter category field: exclude categories that have products directly (level 1 products)
        # This prevents creating subcategories if category already has products
        if db_field.name == "category":
            # Get all categories
            all_categories = Category.objects.all()
            
            # Get categories that have products without subcategory (level 1 products)
            categories_with_products = Product.objects.filter(
                subcategory__isnull=True
            ).values_list('category_id', flat=True).distinct()
            
            # Exclude categories with level 1 products, unless editing existing subcategory
            available_categories = all_categories.exclude(
                pk__in=categories_with_products
            )
            
            # If editing existing subcategory, include its current category even if it has products
            if obj_id:
                try:
                    subcategory = Subcategory.objects.get(pk=obj_id)
                    if subcategory.category:
                        available_categories = available_categories | Category.objects.filter(pk=subcategory.category.pk)
                except Subcategory.DoesNotExist:
                    pass
            
            kwargs["queryset"] = available_categories
        
        # Filter parent_subcategory to only show first-level subcategories from the same category that don't have products
        elif db_field.name == "parent_subcategory":
            # Get the category from the form or request
            obj_id = request.resolver_match.kwargs.get('object_id')
            if obj_id:
                try:
                    subcategory = Subcategory.objects.get(pk=obj_id)
                    category = subcategory.category
                except Subcategory.DoesNotExist:
                    category = None
            else:
                # For new objects, try to get category from request
                category_id = request.GET.get('category')
                if category_id:
                    try:
                        category = Category.objects.get(pk=category_id)
                    except Category.DoesNotExist:
                        category = None
                else:
                    category = None
            
            if category:
                # Only show first-level subcategories (no parent) from the same category
                # that don't have products (to allow creating level 3)
                first_level_subcats = Subcategory.objects.filter(
                    category=category,
                    parent_subcategory__isnull=True
                )
                
                # Exclude subcategories that have products directly assigned (level 2 products)
                # Get IDs of subcategories that have products
                subcats_with_products = Product.objects.filter(
                    subcategory__in=first_level_subcats,
                    second_subcategory__isnull=True
                ).values_list('subcategory_id', flat=True).distinct()
                
                # Filter out subcategories with products
                available_parents = first_level_subcats.exclude(
                    pk__in=subcats_with_products
                )
                
                if obj_id:
                    available_parents = available_parents.exclude(pk=obj_id)
                
                kwargs["queryset"] = available_parents
            else:
                # If no category selected, show all first-level subcategories without products
                first_level_subcats = Subcategory.objects.filter(parent_subcategory__isnull=True)
                subcats_with_products = Product.objects.filter(
                    subcategory__in=first_level_subcats,
                    second_subcategory__isnull=True
                ).values_list('subcategory_id', flat=True).distinct()
                kwargs["queryset"] = first_level_subcats.exclude(pk__in=subcats_with_products)
        
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


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
    fields = ('sku_code', 'size_option', 'color_option', 'price', 'original_price', 'currency', 'stock', 'variant_image', 'is_active')
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
    list_display = ('name', 'brand', 'market', 'gender', 'category', 'subcategory', 'second_subcategory', 'catalog_level_display', 'price', 'discount', 'sales_count', 'rating', 'in_stock', 'is_active')
    list_filter = ('market', 'gender', 'category', 'subcategory', 'second_subcategory', 'brand', 'is_active', 'in_stock', 'is_featured', 'is_best_seller', 'created_at')
    search_fields = ('name', 'brand__name', 'description', 'ai_description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'catalog_level_display')
    
    inlines = [ProductSizeOptionInline, ProductColorOptionInline, SKUInline, ProductImageInline, ProductFeatureInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'brand', 'description', 'market', 'gender')
        }),
        ('Product Attributes (Shown on Frontend)', {
            'fields': ('material_tags', 'season_tags'),
            'description': 'These fields appear in the "О товаре" section on the product page. '
                          'Enter as JSON array: ["cotton", "polyester"] for materials or ["all-season", "summer"] for seasons. '
                          'SKU code (Артикул) is automatically taken from the first SKU.'
        }),
        ('AI-Enhanced Information', {
            'fields': ('ai_description', 'style_tags', 'occasion_tags', 'color_tags', 'age_group_tags', 'activity_tags'),
            'classes': ('collapse',),
            'description': 'These fields help AI understand and recommend products better'
        }),
        ('Categorization - Flexible 3-Level Catalog', {
            'fields': ('category', 'subcategory', 'second_subcategory', 'catalog_level_display'),
            'description': 'Flexible catalog structure:\n'
                          '• Level 1: Category only (leave subcategory and second_subcategory empty)\n'
                          '• Level 2: Category + Subcategory (leave second_subcategory empty)\n'
                          '• Level 3: Category + Subcategory + Second Subcategory (fill all fields)\n\n'
                          'Validation Rules:\n'
                          '• If second_subcategory is set, subcategory must also be set.\n'
                          '• Second subcategory must be a child of the first subcategory.\n'
                          '• Cannot add products to a subcategory that has child subcategories.\n'
                          '• Cannot create child subcategories if parent has products.\n'
                          '• All levels must be unique within their scope.'
        }),
        ('Pricing', {
            'fields': ('price', 'original_price', 'discount', 'currency')
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
    
    def catalog_level_display(self, obj):
        """Display the catalog level of this product"""
        if obj.pk:
            if obj.second_subcategory:
                return "Level 3 (Category → Subcategory → Second Subcategory)"
            elif obj.subcategory:
                return "Level 2 (Category → Subcategory)"
            elif obj.category:
                return "Level 1 (Category only)"
            return "No category"
        return "—"
    catalog_level_display.short_description = 'Catalog Level'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('category', 'subcategory', 'second_subcategory', 'brand', 'currency')
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter subcategories based on selected category and parent relationships"""
        obj_id = request.resolver_match.kwargs.get('object_id')
        
        # Category field: Show all categories - validation will prevent invalid combinations
        if db_field.name == "category":
            # Show all categories - the model validation will enforce the rules
            kwargs["queryset"] = Category.objects.all()
        
        # Filter subcategory field: Show subcategories based on selected category
        elif db_field.name == "subcategory":
            # Get category from form data or existing product
            category_id = request.GET.get('category')
            if obj_id:
                try:
                    product = Product.objects.get(pk=obj_id)
                    category = product.category
                except Product.DoesNotExist:
                    category = None
            elif category_id:
                try:
                    category = Category.objects.get(pk=category_id)
                except Category.DoesNotExist:
                    category = None
            else:
                category = None
            
            if category:
                # Show all first-level subcategories for this category
                # Model validation will prevent adding products to subcategories with children
                kwargs["queryset"] = Subcategory.objects.filter(
                    category=category,
                    parent_subcategory__isnull=True
                )
            else:
                # If no category selected, show all first-level subcategories
                kwargs["queryset"] = Subcategory.objects.filter(parent_subcategory__isnull=True)
        
        elif db_field.name == "second_subcategory":
            # Get the subcategory from the form or existing product
            if obj_id:
                try:
                    product = Product.objects.get(pk=obj_id)
                    subcategory = product.subcategory
                except Product.DoesNotExist:
                    subcategory = None
            else:
                subcategory_id = request.GET.get('subcategory')
                if subcategory_id:
                    try:
                        subcategory = Subcategory.objects.get(pk=subcategory_id)
                    except Subcategory.DoesNotExist:
                        subcategory = None
                else:
                    subcategory = None
            
            if subcategory:
                # Only show second-level subcategories that are children of the selected subcategory
                kwargs["queryset"] = Subcategory.objects.filter(
                    parent_subcategory=subcategory
                )
            else:
                # If no subcategory selected, show all second-level subcategories
                kwargs["queryset"] = Subcategory.objects.filter(parent_subcategory__isnull=False)
        
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(SKU)
class SKUAdmin(admin.ModelAdmin):
    list_display = ('sku_code', 'product', 'size_option', 'color_option', 'price', 'currency', 'stock', 'is_active')
    list_filter = ('is_active', 'currency', 'size_option__name', 'color_option__name', 'created_at')
    search_fields = ('sku_code', 'product__name', 'product__brand')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('product', 'sku_code')
        }),
        ('Variant Attributes', {
            'fields': ('size_option', 'color_option')
        }),
        ('Pricing', {
            'fields': ('price', 'original_price', 'currency')
        }),
        ('Stock & Status', {
            'fields': ('stock', 'variant_image', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


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
