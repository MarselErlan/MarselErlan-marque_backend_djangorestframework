from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, VerificationCode, Address, PaymentMethod, Notification, UserPhoneNumber


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('phone', 'full_name', 'email', 'location', 'is_active', 'is_verified', 'created_at')
    list_filter = ('is_active', 'is_verified', 'is_staff', 'location', 'created_at')
    search_fields = ('phone', 'full_name', 'email')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('phone', 'full_name', 'email', 'profile_image')
        }),
        ('Status', {
            'fields': ('is_active', 'is_verified', 'is_staff', 'is_superuser')
        }),
        ('Location & Localization', {
            'fields': ('location', 'language', 'country', 'currency', 'currency_code')
        }),
        ('Timestamps', {
            'fields': ('last_login', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'last_login')
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone', 'password1', 'password2', 'full_name', 'location'),
        }),
    )
    
    filter_horizontal = ()


@admin.register(VerificationCode)
class VerificationCodeAdmin(admin.ModelAdmin):
    list_display = ('phone', 'market', 'code', 'is_used', 'expires_at', 'created_at')
    list_filter = ('market', 'is_used', 'created_at')
    search_fields = ('phone', 'code')
    ordering = ('-created_at',)
    fieldsets = (
        ('SMS Details', {
            'fields': ('phone', 'market', 'code')
        }),
        ('Status', {
            'fields': ('is_used', 'expires_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
    readonly_fields = ('created_at',)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'market', 'title', 'city', 'state', 'country', 'is_default', 'created_at')
    list_filter = ('market', 'country', 'is_default', 'created_at')
    search_fields = ('user__phone', 'user__first_name', 'user__last_name', 'title', 'full_address', 'city')
    readonly_fields = ('market', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    fieldsets = (
        ('User & Market', {
            'fields': ('user', 'market')
        }),
        ('Address Details', {
            'fields': ('title', 'full_address', 'street', 'building', 'apartment', 'city', 'state', 'postal_code', 'country')
        }),
        ('Settings', {
            'fields': ('is_default',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('user', 'market', 'payment_type', 'card_type', 'card_number_masked', 'is_default', 'created_at')
    list_filter = ('market', 'payment_type', 'card_type', 'is_default', 'created_at')
    search_fields = ('user__phone', 'card_holder_name', 'card_number_masked')
    readonly_fields = ('market', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    fieldsets = (
        ('User & Market', {
            'fields': ('user', 'market')
        }),
        ('Payment Details', {
            'fields': ('payment_type', 'card_type', 'card_number_masked', 'card_holder_name', 'expiry_month', 'expiry_year')
        }),
        ('Settings', {
            'fields': ('is_default',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'market', 'type', 'title', 'is_read', 'created_at')
    list_filter = ('market', 'type', 'is_read', 'created_at')
    search_fields = ('user__phone', 'title', 'message')
    readonly_fields = ('market', 'created_at')
    ordering = ('-created_at',)
    fieldsets = (
        ('User & Market', {
            'fields': ('user', 'market')
        }),
        ('Notification Details', {
            'fields': ('type', 'title', 'message', 'order_id')
        }),
        ('Status', {
            'fields': ('is_read',)
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )


@admin.register(UserPhoneNumber)
class UserPhoneNumberAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'label', 'is_primary', 'created_at')
    list_filter = ('is_primary', 'created_at')
    search_fields = ('user__phone', 'phone', 'label')
    ordering = ('-is_primary', '-created_at')
