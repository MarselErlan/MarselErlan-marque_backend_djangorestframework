"""
Admin configuration for Delivery Fee app.
"""

from django.contrib import admin
from .models import DeliveryFee


@admin.register(DeliveryFee)
class DeliveryFeeAdmin(admin.ModelAdmin):
    """Admin interface for DeliveryFee model."""
    
    list_display = [
        'fee_path',
        'fee_display',
        'is_active',
        'created_at',
    ]
    
    list_filter = [
        'is_active',
        'category',
        'created_at',
    ]
    
    search_fields = [
        'category__name',
        'subcategory__name',
        'second_subcategory__name',
        'description',
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        ('Category Structure', {
            'fields': ('category', 'subcategory', 'second_subcategory'),
            'description': 'Set fee based on category structure. More specific (with more levels) takes precedence.'
        }),
        ('Fee Configuration', {
            'fields': ('fee_amount', 'description'),
            'description': 'Delivery fee amount for products in this category structure.'
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related(
            'category',
            'subcategory',
            'second_subcategory'
        )
    
    def fee_path(self, obj):
        """Display the category path for this fee"""
        parts = [obj.category.name]
        if obj.subcategory:
            parts.append(obj.subcategory.name)
        if obj.second_subcategory:
            parts.append(obj.second_subcategory.name)
        return ' → '.join(parts)
    fee_path.short_description = 'Category Path'
    fee_path.admin_order_field = 'category__name'
    
    def fee_display(self, obj):
        """Display fee in a readable format"""
        return f"${obj.fee_amount}" if obj.fee_amount > 0 else "No fee"
    fee_display.short_description = 'Delivery Fee'
    fee_display.admin_order_field = 'fee_amount'
