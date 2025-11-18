from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
import uuid


class CustomUserManager(BaseUserManager):
    """Custom user manager for phone-based authentication"""
    
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError('Phone number is required')
        
        user = self.model(phone=phone, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_verified', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(phone, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom User model with phone authentication"""
    
    LOCATION_CHOICES = [
        ('KG', 'Kyrgyzstan'),
        ('US', 'United States'),
    ]

    LOCATION_DEFAULTS = {
        'KG': {
            'country': 'Kyrgyzstan',
            'currency': 'сом',
            'currency_code': 'KGS',
        },
        'US': {
            'country': 'United States',
            'currency': '$',
            'currency_code': 'USD',
        },
    }
    
    LANGUAGE_CHOICES = [
        ('ru', 'Russian'),
        ('en', 'English'),
        ('ky', 'Kyrgyz'),
    ]
    
    id = models.AutoField(primary_key=True)
    phone = models.CharField(max_length=20, unique=True, db_index=True)
    full_name = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(max_length=255, null=True, blank=True)
    profile_image = models.ImageField(
        upload_to='users/profile_images/',
        null=True,
        blank=True,
    )
    
    # Status fields
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    
    # Market and localization
    location = models.CharField(max_length=2, choices=LOCATION_CHOICES, default='KG')
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default='ru')
    country = models.CharField(max_length=50, default='Kyrgyzstan')
    currency = models.CharField(max_length=10, default='сом')
    currency_code = models.CharField(max_length=3, default='KGS')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.phone
    
    @property
    def name(self):
        """Alias for full_name for API compatibility"""
        return self.full_name
    
    @property
    def formatted_phone(self):
        """Return formatted phone number"""
        return self.get_formatted_phone()
    
    def get_formatted_phone(self):
        """Return formatted phone number (method version for serializer)"""
        # Simple formatting for Kyrgyz numbers
        if self.phone.startswith('+996') and len(self.phone) == 13:
            return f"+996 {self.phone[4:7]} {self.phone[7:9]} {self.phone[9:11]} {self.phone[11:13]}"
        # US phone formatting
        elif self.phone.startswith('+1') and len(self.phone) == 12:
            return f"+1 ({self.phone[2:5]}) {self.phone[5:8]}-{self.phone[8:12]}"
        return self.phone
    
    def get_full_name(self):
        """Get full name (method version for views)"""
        return self.full_name or ''
    
    def get_country(self):
        """Get country based on market"""
        if self.location == 'KG':
            return 'Kyrgyzstan'
        elif self.location == 'US':
            return 'United States'
        return self.country
    
    def get_currency(self):
        """Get currency symbol based on market"""
        if self.location == 'KG':
            return 'сом'
        elif self.location == 'US':
            return '$'
        return 'сом'
    
    def get_currency_code(self):
        """Get currency code based on market"""
        if self.location == 'KG':
            return 'KGS'
        elif self.location == 'US':
            return 'USD'
        return 'KGS'

    def save(self, *args, **kwargs):
        """Ensure country and currency fields stay aligned with location."""
        defaults = self.LOCATION_DEFAULTS.get(self.location)
        if defaults:
            self.country = defaults['country']
            self.currency = defaults['currency']
            self.currency_code = defaults['currency_code']
        super().save(*args, **kwargs)


class VerificationCode(models.Model):
    """OTP verification codes for phone authentication
    
    Note: Market field is used to determine SMS provider:
    - KG: Local SMS provider (e.g., Beeline, MegaCom)
    - US: International provider (e.g., Twilio, AWS SNS)
    """
    
    MARKET_CHOICES = [
        ('KG', 'Kyrgyzstan'),
        ('US', 'United States'),
    ]
    
    phone = models.CharField(max_length=20, db_index=True)
    code = models.CharField(max_length=6)
    market = models.CharField(max_length=2, choices=MARKET_CHOICES, default='KG', db_index=True)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'verification_codes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone', 'code', 'is_used']),
            models.Index(fields=['market', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.phone} - {self.code}"
    
    def is_valid(self):
        """Check if code is still valid"""
        return not self.is_used and timezone.now() < self.expires_at


class Address(models.Model):
    """User delivery addresses
    
    Note: Market field determines:
    - Address format validation (KG vs US format)
    - Delivery service (local courier vs international shipping)
    - Country auto-set based on market
    """
    
    MARKET_CHOICES = [
        ('KG', 'Kyrgyzstan'),
        ('US', 'United States'),
    ]
    COUNTRY_CHOICES = [
        ('Kyrgyzstan', 'Kyrgyzstan'),
        ('United States', 'United States'),
    ]
    MARKET_COUNTRY_MAP = {
        'KG': 'Kyrgyzstan',
        'US': 'United States',
    }
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    market = models.CharField(max_length=2, choices=MARKET_CHOICES, default='KG', db_index=True)
    title = models.CharField(max_length=100)  # e.g., "Home", "Work"
    full_address = models.TextField()
    street = models.CharField(max_length=255, null=True, blank=True)
    building = models.CharField(max_length=50, null=True, blank=True)
    apartment = models.CharField(max_length=50, null=True, blank=True)
    entrance = models.CharField(max_length=20, null=True, blank=True)  # Подъезд (for KG addresses)
    floor = models.CharField(max_length=20, null=True, blank=True)  # Этаж (for KG addresses)
    comment = models.TextField(null=True, blank=True, max_length=200)  # Комментарий к заказу
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)  # For US addresses
    postal_code = models.CharField(max_length=20, null=True, blank=True)
    country = models.CharField(max_length=100, choices=COUNTRY_CHOICES, default='Kyrgyzstan')
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'addresses'
        verbose_name = 'Address'
        verbose_name_plural = 'Addresses'
        ordering = ['-is_default', '-created_at']
        indexes = [
            models.Index(fields=['user', 'market']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.full_address}"
    
    def save(self, *args, **kwargs):
        # Auto-populate market and country from user
        if self.user:
            if not self.market:
                self.market = self.user.location
            if self.market in self.MARKET_COUNTRY_MAP:
                self.country = self.MARKET_COUNTRY_MAP[self.market]
        
        # If this address is set as default, unset other defaults for same market
        if self.is_default and self.user_id:
            Address.objects.filter(
                user=self.user,
                market=self.market,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class PaymentMethod(models.Model):
    """User payment methods
    
    Note: Market field determines:
    - Payment gateway (KG: local banks, US: Stripe/PayPal)
    - Available payment methods (MIR cards only in KG)
    - Currency processing
    """
    
    PAYMENT_TYPE_CHOICES = [
        ('card', 'Credit/Debit Card'),
        ('cash', 'Cash on Delivery'),
        ('bank_transfer', 'Bank Transfer'),  # Popular in KG
        ('digital_wallet', 'Digital Wallet'),  # e.g., MBank, PayPal
    ]
    
    CARD_TYPE_CHOICES = [
        ('visa', 'Visa'),
        ('mastercard', 'Mastercard'),
        ('mir', 'MIR'),  # Only available in KG market
        ('amex', 'American Express'),  # More common in US
        ('other', 'Unknown'),
    ]
    
    MARKET_CHOICES = [
        ('KG', 'Kyrgyzstan'),
        ('US', 'United States'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_methods')
    market = models.CharField(max_length=2, choices=MARKET_CHOICES, default='KG', db_index=True)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES, default='card')
    card_type = models.CharField(max_length=20, choices=CARD_TYPE_CHOICES, default='visa')
    card_number_masked = models.CharField(max_length=19)  # **** **** **** 1234
    card_holder_name = models.CharField(max_length=255)
    expiry_month = models.CharField(max_length=2, null=True, blank=True)
    expiry_year = models.CharField(max_length=4, null=True, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payment_methods'
        verbose_name = 'Payment Method'
        verbose_name_plural = 'Payment Methods'
        ordering = ['-is_default', '-created_at']
        indexes = [
            models.Index(fields=['user', 'market']),
        ]
    
    def __str__(self):
        return f"{self.user.phone} - {self.card_type} {self.card_number_masked} ({self.market})"
    
    def get_card_type(self):
        """Get human-readable card type"""
        card_types = dict(self.CARD_TYPE_CHOICES)
        return card_types.get(self.card_type, 'Unknown')
    
    def save(self, *args, **kwargs):
        # Auto-populate market from user on creation
        if not self.pk and self.user:
            self.market = self.user.location
        
        # Auto-detect card type from card number
        if self.card_number_masked:
            first_digit = self.card_number_masked[0] if self.card_number_masked else None
            if first_digit == '4':
                self.card_type = 'visa'
            elif first_digit == '5':
                self.card_type = 'mastercard'
            elif first_digit == '3':
                self.card_type = 'amex'
            elif first_digit == '2':
                self.card_type = 'mir'
            elif first_digit == '*' or not first_digit.isdigit():
                self.card_type = 'other'  # Masked or unknown
        
        # If this payment method is set as default, unset other defaults for same market
        if self.is_default:
            PaymentMethod.objects.filter(user=self.user, market=self.market, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class Notification(models.Model):
    """User notifications
    
    Note: Market field is used for:
    - Localized messaging (language varies by market)
    - Market-specific promotions
    - Delivery status formatting (different couriers)
    """
    
    TYPE_CHOICES = [
        ('order', 'Order Update'),
        ('delivery', 'Delivery Update'),
        ('promotion', 'Promotion'),
        ('system', 'System'),
    ]
    
    MARKET_CHOICES = [
        ('KG', 'Kyrgyzstan'),
        ('US', 'United States'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    market = models.CharField(max_length=2, choices=MARKET_CHOICES, default='KG', db_index=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='system')
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    order_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notifications'
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['market', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.phone} - {self.title} ({self.market})"
    
    def save(self, *args, **kwargs):
        # Auto-populate market from user on creation
        if not self.pk and self.user:
            self.market = self.user.location
        super().save(*args, **kwargs)


class UserPhoneNumber(models.Model):
    """Additional phone numbers for user contact."""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='phone_numbers')
    label = models.CharField(max_length=100, null=True, blank=True)
    phone = models.CharField(max_length=20)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_phone_numbers'
        verbose_name = 'Phone Number'
        verbose_name_plural = 'Phone Numbers'
        unique_together = ('user', 'phone')
        ordering = ['-is_primary', '-created_at']
        indexes = [
            models.Index(fields=['user', 'phone']),
            models.Index(fields=['user', '-is_primary', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.phone} - {self.phone}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_primary:
            UserPhoneNumber.objects.filter(
                user=self.user,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
