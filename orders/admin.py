from django.contrib import admin
from .models import Order, OrderItem, OrderStatusHistory, Review, ReviewImage


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ('product_name', 'product_brand', 'size', 'color', 'price', 'quantity', 'subtotal')
    readonly_fields = ('subtotal',)


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    fields = ('status', 'notes', 'changed_by', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'market', 'customer_name', 'customer_phone', 'status', 'total_amount', 'payment_method', 'card_type', 'order_date')
    list_filter = ('market', 'status', 'payment_method', 'card_type', 'payment_status', 'order_date', 'created_at')
    search_fields = ('order_number', 'customer_name', 'customer_phone', 'customer_email', 'user__phone', 'card_last_four')
    ordering = ('-created_at',)
    readonly_fields = ('order_number', 'market', 'delivery_country', 'card_last_four', 'order_date', 'created_at', 'updated_at', 'items_count', 'is_active', 'can_cancel')
    
    inlines = [OrderItemInline, OrderStatusHistoryInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'market', 'status')
        }),
        ('References', {
            'fields': ('shipping_address', 'payment_method_used'),
            'description': 'Links to the address and payment method used (for history tracking)'
        }),
        ('Customer Information', {
            'fields': ('customer_name', 'customer_phone', 'customer_email')
        }),
        ('Delivery Information (Snapshot)', {
            'fields': ('delivery_address', 'delivery_city', 'delivery_state', 'delivery_postal_code', 'delivery_country', 'delivery_notes', 'requested_delivery_date'),
            'description': 'Snapshot of delivery info at order time. requested_delivery_date is when customer wants delivery.'
        }),
        ('Payment (Snapshot)', {
            'fields': ('payment_method', 'card_type', 'card_last_four', 'payment_status'),
            'description': 'Snapshot of payment info at order time'
        }),
        ('Pricing', {
            'fields': ('subtotal', 'shipping_cost', 'tax', 'total_amount', 'currency', 'currency_code')
        }),
        ('Timestamps', {
            'fields': ('order_date', 'confirmed_date', 'shipped_date', 'delivered_date', 'cancelled_date', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('items_count', 'is_active', 'can_cancel'),
            'classes': ('collapse',)
        }),
    )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product_name', 'size', 'color', 'price', 'quantity', 'subtotal')
    search_fields = ('order__order_number', 'product_name', 'product_brand')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'subtotal')


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('order', 'status', 'changed_by', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order__order_number', 'notes')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)


class ReviewImageInline(admin.TabularInline):
    model = ReviewImage
    extra = 1
    fields = ('image', 'image_url')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'rating', 'is_verified_purchase', 'is_approved', 'created_at')
    list_filter = ('rating', 'is_verified_purchase', 'is_approved', 'created_at')
    search_fields = ('user__phone', 'product__name', 'title', 'comment')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    
    inlines = [ReviewImageInline]
    
    fieldsets = (
        ('Review Information', {
            'fields': ('user', 'product', 'order', 'rating')
        }),
        ('Content', {
            'fields': ('title', 'comment')
        }),
        ('Status', {
            'fields': ('is_verified_purchase', 'is_approved')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ReviewImage)
class ReviewImageAdmin(admin.ModelAdmin):
    list_display = ('review', 'image', 'created_at')
    search_fields = ('review__user__phone', 'review__product__name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    fields = ('review', 'image', 'image_url', 'created_at')
