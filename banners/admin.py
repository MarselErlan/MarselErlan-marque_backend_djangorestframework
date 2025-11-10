from django.contrib import admin
from .models import Banner


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'banner_type', 'market', 'is_active', 'sort_order', 'view_count', 'click_count', 'ctr', 'created_at')
    list_filter = ('market', 'banner_type', 'is_active', 'created_at')
    search_fields = ('title', 'subtitle')
    ordering = ('market', 'sort_order', '-created_at')
    readonly_fields = ('created_at', 'updated_at', 'view_count', 'click_count', 'ctr')
    
    fieldsets = (
        ('Content', {
            'fields': ('title', 'subtitle', 'image', 'image_url')
        }),
        ('Type & Settings', {
            'fields': ('banner_type', 'market', 'is_active', 'sort_order')
        }),
        ('Call to Action', {
            'fields': ('button_text', 'link_url')
        }),
        ('Scheduling (Optional)', {
            'fields': ('start_date', 'end_date'),
            'classes': ('collapse',)
        }),
        ('Analytics', {
            'fields': ('view_count', 'click_count', 'ctr'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
