"""
Admin configuration for Referral Fee app.
"""

from django.contrib import admin
from .models import ReferralFee


@admin.register(ReferralFee)
class ReferralFeeAdmin(admin.ModelAdmin):
    """Admin interface for ReferralFee model."""
    
    list_display = [
        'category',
        'subcategory',
        'second_subcategory',
        'fee_percentage',
        'fee_fixed',
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
            'fields': ('fee_percentage', 'fee_fixed', 'description'),
            'description': 'Fee can be percentage-based, fixed, or both.'
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
