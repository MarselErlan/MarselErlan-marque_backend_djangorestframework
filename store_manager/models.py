from django.db import models
from users.models import User
from orders.models import Order
from django.core.validators import MinValueValidator


class StoreManager(models.Model):
    """Store Manager/Admin - Special role for managing orders and analytics"""
    
    MANAGER_ROLE_CHOICES = [
        ('admin', 'Admin'),  # Full access
        ('manager', 'Manager'),  # Order management only
        ('viewer', 'Viewer'),  # Read-only access
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='manager_profile')
    role = models.CharField(max_length=20, choices=MANAGER_ROLE_CHOICES, default='manager')
    
    # Market management - Which markets this manager can access
    can_manage_kg = models.BooleanField(default=True)
    can_manage_us = models.BooleanField(default=False)
    
    # Permissions
    can_view_orders = models.BooleanField(default=True)
    can_edit_orders = models.BooleanField(default=True)
    can_cancel_orders = models.BooleanField(default=True)
    can_view_revenue = models.BooleanField(default=True)
    can_export_data = models.BooleanField(default=False)
    
    # Activity
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'store_managers'
        verbose_name = 'Store Manager'
        verbose_name_plural = 'Store Managers'
    
    def __str__(self):
        return f"{self.user.full_name or self.user.phone} - {self.get_role_display()}"
    
    @property
    def accessible_markets(self):
        """Get list of markets this manager can access"""
        markets = []
        if self.can_manage_kg:
            markets.append('KG')
        if self.can_manage_us:
            markets.append('US')
        return markets


class ManagerSettings(models.Model):
    """Manager preferences and settings"""
    
    LANGUAGE_CHOICES = [
        ('ru', 'Русский'),
        ('ky', 'Кыргызча'),
        ('en', 'English'),
    ]
    
    THEME_CHOICES = [
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('system', 'System'),
    ]
    
    MARKET_CHOICES = [
        ('KG', 'Kyrgyzstan'),
        ('US', 'United States'),
    ]
    
    manager = models.OneToOneField(StoreManager, on_delete=models.CASCADE, related_name='settings')
    
    # UI Preferences
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default='ru')
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='light')
    
    # Current active market filter (manager switches view between markets in same DB)
    active_market = models.CharField(max_length=2, choices=MARKET_CHOICES, default='KG')  # KG or US
    
    # Notification Settings
    notify_new_orders = models.BooleanField(default=True)
    notify_status_changes = models.BooleanField(default=True)
    notify_daily_report = models.BooleanField(default=True)
    notify_delivery_errors = models.BooleanField(default=False)
    
    # Email for reports
    report_email = models.EmailField(null=True, blank=True)
    
    # Dashboard preferences
    default_order_filter = models.CharField(max_length=20, default='Все')  # Все, Ожидание, В пути, Доставлено
    orders_per_page = models.IntegerField(default=20)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'manager_settings'
        verbose_name = 'Manager Settings'
        verbose_name_plural = 'Manager Settings'
    
    def __str__(self):
        return f"Settings - {self.manager.user.phone}"


class RevenueSnapshot(models.Model):
    """Daily and hourly revenue snapshots for analytics
    
    Note: All data is stored in ONE database. The 'market' field is used to 
    filter/separate analytics by market (KG vs US orders from user.location).
    """
    
    SNAPSHOT_TYPE_CHOICES = [
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    MARKET_CHOICES = [
        ('KG', 'Kyrgyzstan'),
        ('US', 'United States'),
    ]
    
    # Market filter (separates analytics by user.location, not different databases)
    market = models.CharField(max_length=2, choices=MARKET_CHOICES, default='KG', db_index=True)
    
    # Time period
    snapshot_type = models.CharField(max_length=10, choices=SNAPSHOT_TYPE_CHOICES, default='daily')
    snapshot_date = models.DateField(db_index=True)
    snapshot_hour = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)])  # 0-23 for hourly
    
    # Revenue metrics
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default='сом')
    currency_code = models.CharField(max_length=3, default='KGS')
    
    # Order metrics
    total_orders = models.IntegerField(default=0)
    completed_orders = models.IntegerField(default=0)
    cancelled_orders = models.IntegerField(default=0)
    pending_orders = models.IntegerField(default=0)
    
    # Average metrics
    average_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Comparison with previous period
    revenue_change_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, null=True, blank=True)
    orders_change_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'revenue_snapshots'
        verbose_name = 'Revenue Snapshot'
        verbose_name_plural = 'Revenue Snapshots'
        ordering = ['-snapshot_date', '-snapshot_hour']
        unique_together = ['market', 'snapshot_type', 'snapshot_date', 'snapshot_hour']
        indexes = [
            models.Index(fields=['market', 'snapshot_date']),
            models.Index(fields=['snapshot_type', 'snapshot_date']),
        ]
    
    def __str__(self):
        if self.snapshot_hour is not None:
            return f"{self.market} - {self.snapshot_date} {self.snapshot_hour}:00 - {self.total_revenue} {self.currency_code}"
        return f"{self.market} - {self.snapshot_date} - {self.total_revenue} {self.currency_code}"


class ManagerActivityLog(models.Model):
    """Track manager actions for audit purposes
    
    Note: 'market' field indicates which market filter was active when action occurred.
    """
    
    ACTION_TYPE_CHOICES = [
        ('view_order', 'Viewed Order'),
        ('update_status', 'Updated Order Status'),
        ('cancel_order', 'Cancelled Order'),
        ('resume_order', 'Resumed Order'),
        ('export_data', 'Exported Data'),
        ('view_revenue', 'Viewed Revenue'),
        ('switch_market', 'Switched Market View'),  # Switching filter, not DB
        ('login', 'Logged In'),
        ('logout', 'Logged Out'),
    ]
    
    MARKET_CHOICES = [
        ('KG', 'Kyrgyzstan'),
        ('US', 'United States'),
    ]
    
    manager = models.ForeignKey(StoreManager, on_delete=models.CASCADE, related_name='activity_logs')
    action_type = models.CharField(max_length=20, choices=ACTION_TYPE_CHOICES, db_index=True)
    
    # Context
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='manager_logs')
    market = models.CharField(max_length=2, choices=MARKET_CHOICES, null=True, blank=True)  # Market filter active during action
    
    # Details
    description = models.TextField(null=True, blank=True)
    old_value = models.CharField(max_length=255, null=True, blank=True)  # e.g., old status
    new_value = models.CharField(max_length=255, null=True, blank=True)  # e.g., new status
    
    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'manager_activity_logs'
        verbose_name = 'Manager Activity Log'
        verbose_name_plural = 'Manager Activity Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['manager', '-created_at']),
            models.Index(fields=['action_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.manager.user.phone} - {self.get_action_type_display()} - {self.created_at}"


class DailyReport(models.Model):
    """Generated daily reports for managers
    
    Note: Reports are generated per market (based on filtering orders by user.location).
    """
    
    REPORT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('generated', 'Generated'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]
    
    MARKET_CHOICES = [
        ('KG', 'Kyrgyzstan'),
        ('US', 'United States'),
    ]
    
    # Target
    manager = models.ForeignKey(StoreManager, on_delete=models.CASCADE, related_name='reports')
    market = models.CharField(max_length=2, choices=MARKET_CHOICES, default='KG')  # Report for this market's data
    
    # Report period
    report_date = models.DateField(db_index=True)
    
    # Status
    status = models.CharField(max_length=20, choices=REPORT_STATUS_CHOICES, default='pending')
    
    # Report data (JSON)
    report_data = models.JSONField(default=dict)  # Contains revenue, orders, etc.
    
    # Email
    sent_to_email = models.EmailField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    # Error tracking
    error_message = models.TextField(null=True, blank=True)
    retry_count = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'daily_reports'
        verbose_name = 'Daily Report'
        verbose_name_plural = 'Daily Reports'
        ordering = ['-report_date']
        unique_together = ['manager', 'market', 'report_date']
    
    def __str__(self):
        return f"Report - {self.manager.user.phone} - {self.market} - {self.report_date}"


class ManagerNotification(models.Model):
    """In-app notifications for managers
    
    Note: 'market' indicates which market the notification is related to (from user.location).
    """
    
    NOTIFICATION_TYPE_CHOICES = [
        ('new_order', 'New Order'),
        ('status_change', 'Order Status Changed'),
        ('delivery_error', 'Delivery Error'),
        ('system', 'System Notification'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    MARKET_CHOICES = [
        ('KG', 'Kyrgyzstan'),
        ('US', 'United States'),
    ]
    
    manager = models.ForeignKey(StoreManager, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE_CHOICES, default='system')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Content
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    # Related objects
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)
    market = models.CharField(max_length=2, choices=MARKET_CHOICES, null=True, blank=True)  # Related market
    
    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Action URL (optional)
    action_url = models.CharField(max_length=500, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'manager_notifications'
        verbose_name = 'Manager Notification'
        verbose_name_plural = 'Manager Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['manager', 'is_read', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.manager.user.phone} - {self.title}"
