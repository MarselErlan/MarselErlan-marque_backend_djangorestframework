from django.contrib import admin
from .models import (StoreManager, ManagerSettings, RevenueSnapshot, 
                     ManagerActivityLog, DailyReport, ManagerNotification)


@admin.register(StoreManager)
class StoreManagerAdmin(admin.ModelAdmin):
    list_display = ('user', 'store', 'role', 'accessible_markets_display', 'is_active', 'last_login', 'created_at')
    list_filter = ('role', 'store', 'is_active', 'can_manage_kg', 'can_manage_us', 'created_at')
    search_fields = ('user__phone', 'user__full_name', 'store__name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'accessible_markets')
    
    fieldsets = (
        ('Manager Information', {
            'fields': ('user', 'store', 'role', 'is_active', 'last_login')
        }),
        ('Market Access', {
            'fields': ('can_manage_kg', 'can_manage_us', 'accessible_markets')
        }),
        ('Permissions', {
            'fields': (
                'can_view_orders', 
                'can_edit_orders', 
                'can_cancel_orders', 
                'can_view_revenue', 
                'can_export_data'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related to avoid N+1 queries"""
        qs = super().get_queryset(request)
        try:
            # Try to use select_related if store field exists
            return qs.select_related('user', 'store')
        except Exception:
            # Fallback if store field doesn't exist (migration not run)
            return qs.select_related('user')
    
    def accessible_markets_display(self, obj):
        markets = obj.accessible_markets
        return ', '.join(markets) if markets else 'None'
    accessible_markets_display.short_description = 'Markets'


@admin.register(ManagerSettings)
class ManagerSettingsAdmin(admin.ModelAdmin):
    list_display = ('manager', 'language', 'theme', 'active_market', 'notify_new_orders', 'updated_at')
    list_filter = ('language', 'theme', 'active_market', 'notify_new_orders', 'notify_status_changes')
    search_fields = ('manager__user__phone', 'manager__user__full_name')
    ordering = ('-updated_at',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Manager', {
            'fields': ('manager',)
        }),
        ('UI Preferences', {
            'fields': ('language', 'theme', 'active_market')
        }),
        ('Notifications', {
            'fields': (
                'notify_new_orders', 
                'notify_status_changes', 
                'notify_daily_report', 
                'notify_delivery_errors',
                'report_email'
            )
        }),
        ('Dashboard Settings', {
            'fields': ('default_order_filter', 'orders_per_page')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(RevenueSnapshot)
class RevenueSnapshotAdmin(admin.ModelAdmin):
    list_display = ('market', 'snapshot_type', 'snapshot_date', 'snapshot_hour', 'total_revenue', 'total_orders', 'average_order_value')
    list_filter = ('market', 'snapshot_type', 'snapshot_date')
    search_fields = ('market',)
    ordering = ('-snapshot_date', '-snapshot_hour')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Period', {
            'fields': ('market', 'snapshot_type', 'snapshot_date', 'snapshot_hour')
        }),
        ('Revenue Metrics', {
            'fields': ('total_revenue', 'currency', 'currency_code')
        }),
        ('Order Metrics', {
            'fields': ('total_orders', 'completed_orders', 'cancelled_orders', 'pending_orders', 'average_order_value')
        }),
        ('Changes', {
            'fields': ('revenue_change_percent', 'orders_change_percent')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ManagerActivityLog)
class ManagerActivityLogAdmin(admin.ModelAdmin):
    list_display = ('manager', 'action_type', 'order', 'market', 'created_at')
    list_filter = ('action_type', 'market', 'created_at')
    search_fields = ('manager__user__phone', 'manager__user__full_name', 'description', 'order__order_number')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Manager & Action', {
            'fields': ('manager', 'action_type', 'market')
        }),
        ('Context', {
            'fields': ('order', 'description', 'old_value', 'new_value')
        }),
        ('Metadata', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )


@admin.register(DailyReport)
class DailyReportAdmin(admin.ModelAdmin):
    list_display = ('manager', 'market', 'report_date', 'status', 'sent_at', 'retry_count')
    list_filter = ('status', 'market', 'report_date')
    search_fields = ('manager__user__phone', 'manager__user__full_name')
    ordering = ('-report_date',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Report Information', {
            'fields': ('manager', 'market', 'report_date', 'status')
        }),
        ('Report Data', {
            'fields': ('report_data',)
        }),
        ('Email Delivery', {
            'fields': ('sent_to_email', 'sent_at')
        }),
        ('Error Tracking', {
            'fields': ('error_message', 'retry_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ManagerNotification)
class ManagerNotificationAdmin(admin.ModelAdmin):
    list_display = ('manager', 'notification_type', 'priority', 'title', 'is_read', 'created_at')
    list_filter = ('notification_type', 'priority', 'is_read', 'market', 'created_at')
    search_fields = ('manager__user__phone', 'title', 'message')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Notification Details', {
            'fields': ('manager', 'notification_type', 'priority')
        }),
        ('Content', {
            'fields': ('title', 'message', 'action_url')
        }),
        ('Related Objects', {
            'fields': ('order', 'market')
        }),
        ('Status', {
            'fields': ('is_read', 'read_at')
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )
