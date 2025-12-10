from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from users.models import User, Address, PaymentMethod
from products.models import SKU, Product
import random
import string


def generate_order_number():
    """Generate unique order number"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))


class Order(models.Model):
    """Customer orders
    
    Note: This model uses a SNAPSHOT pattern:
    - Links to Address/PaymentMethod for reference (can be null if deleted)
    - BUT snapshots the data at order time (customer_name, delivery_address, etc.)
    - This ensures order data remains intact even if user updates/deletes their info
    
    Market field is stored directly for:
    - Better query performance (no JOIN needed)
    - Easier manager filtering
    - Consistent architecture with Product/Category/Banner
    
    Store Relationship:
    - Orders are linked to stores through OrderItem -> SKU -> Product -> Store
    - An order can contain products from multiple stores
    - Store managers see orders that contain products from their store
    - Use get_stores() method to get all stores in an order
    - Use has_store_products(store) to check if order has products from a specific store
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('card', 'Credit/Debit Card'),
        ('cash', 'Cash on Delivery'),
        ('transfer', 'Bank Transfer'),
        ('digital_wallet', 'Digital Wallet'),
    ]
    
    MARKET_CHOICES = [
        ('KG', 'Kyrgyzstan'),
        ('US', 'United States'),
    ]
    
    # Order identification
    order_number = models.CharField(max_length=20, unique=True, default=generate_order_number, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='orders')
    
    # Market (copied from user.location at order creation for performance)
    market = models.CharField(max_length=2, choices=MARKET_CHOICES, default='KG', db_index=True)
    
    # References to user's address/payment (can be null if user deletes them)
    shipping_address = models.ForeignKey(
        Address, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='orders_shipped_to',
        help_text="Reference to the address used (preserved for history even if address is deleted)"
    )
    payment_method_used = models.ForeignKey(
        PaymentMethod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders_paid_with',
        help_text="Reference to the payment method used (preserved for history)"
    )
    
    # Customer information (SNAPSHOT - preserved at order time)
    customer_name = models.CharField(max_length=255)
    customer_phone = models.CharField(max_length=20)
    customer_email = models.EmailField(null=True, blank=True)
    
    # Delivery information (SNAPSHOT - preserved at order time)
    delivery_address = models.TextField()
    delivery_city = models.CharField(max_length=100, null=True, blank=True)
    delivery_state = models.CharField(max_length=100, null=True, blank=True)  # For US orders
    delivery_postal_code = models.CharField(max_length=20, null=True, blank=True)
    delivery_country = models.CharField(max_length=100, default='Kyrgyzstan')
    delivery_notes = models.TextField(null=True, blank=True)
    requested_delivery_date = models.DateField(null=True, blank=True, help_text="Date when customer wants the order delivered")
    
    # Order status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    
    # Payment (SNAPSHOT - preserved at order time)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cash')
    payment_status = models.CharField(max_length=20, default='pending')  # pending, paid, failed
    card_type = models.CharField(max_length=20, null=True, blank=True)  # visa, mastercard, mir, amex
    card_last_four = models.CharField(max_length=4, null=True, blank=True)  # Last 4 digits
    
    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=350)  # Default from frontend
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='сом')
    currency_code = models.CharField(max_length=3, default='KGS')
    
    # Timestamps
    order_date = models.DateTimeField(auto_now_add=True)
    confirmed_date = models.DateTimeField(null=True, blank=True)
    shipped_date = models.DateTimeField(null=True, blank=True)
    delivered_date = models.DateTimeField(null=True, blank=True)
    cancelled_date = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'orders'
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['market', 'status']),  # Main manager filtering index
            models.Index(fields=['user', 'status']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['market', '-created_at']),  # For manager dashboard
        ]
    
    def save(self, *args, **kwargs):
        # Auto-populate market from user on creation
        if not self.pk and self.user:
            self.market = self.user.location
            
            # Auto-populate delivery country based on market
            if not self.delivery_country:
                self.delivery_country = 'Kyrgyzstan' if self.market == 'KG' else 'United States'
            
            # Snapshot data from shipping_address if provided
            if self.shipping_address:
                self.delivery_address = self.shipping_address.full_address
                self.delivery_city = self.shipping_address.city
                self.delivery_state = self.shipping_address.state
                self.delivery_postal_code = self.shipping_address.postal_code
                self.delivery_country = self.shipping_address.country
            
            # Snapshot data from payment_method_used if provided
            if self.payment_method_used:
                self.payment_method = self.payment_method_used.payment_type
                self.card_type = self.payment_method_used.card_type
                # Extract last 4 digits from masked number (e.g., "**** **** **** 1234")
                if self.payment_method_used.card_number_masked:
                    self.card_last_four = self.payment_method_used.card_number_masked.replace('*', '').replace(' ', '')[-4:]
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Order {self.order_number} - {self.customer_name}"
    
    @property
    def items_count(self):
        return sum(item.quantity for item in self.items.all())
    
    @property
    def delivery_date(self):
        """Expected delivery date (can be calculated or set)"""
        return self.delivered_date
    
    @property
    def is_active(self):
        """Check if order is still active (not delivered/cancelled)"""
        return self.status not in ['delivered', 'cancelled', 'refunded']
    
    @property
    def can_cancel(self):
        """Check if order can be cancelled"""
        return self.status in ['pending', 'confirmed']
    
    def get_stores(self):
        """Get all stores associated with this order through products.
        
        Returns:
            QuerySet of Store objects that have products in this order.
        """
        from stores.models import Store
        # Get unique stores from order items
        store_ids = self.items.filter(
            sku__product__store__isnull=False
        ).values_list('sku__product__store', flat=True).distinct()
        
        return Store.objects.filter(id__in=store_ids)
    
    def has_store_products(self, store):
        """Check if order contains products from a specific store.
        
        Args:
            store: Store instance or store ID
            
        Returns:
            bool: True if order has products from the store
        """
        store_id = store.id if hasattr(store, 'id') else store
        return self.items.filter(
            sku__product__store_id=store_id
        ).exists()


class OrderItem(models.Model):
    """Items in an order
    
    Note: Referral fees are calculated and stored per item at order creation time.
    This ensures fees are locked in even if fee configurations change later.
    """
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    sku = models.ForeignKey(SKU, on_delete=models.SET_NULL, null=True)
    
    # Product information (snapshot at time of order)
    product_name = models.CharField(max_length=255)
    product_brand = models.CharField(max_length=100)
    size = models.CharField(max_length=20)
    color = models.CharField(max_length=50)
    image_url = models.URLField(max_length=500, null=True, blank=True)
    
    # Pricing (snapshot at time of order)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Referral fee (snapshot at time of order)
    referral_fee_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Referral fee percentage applied to this item"
    )
    referral_fee_fixed = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Fixed referral fee amount for this item"
    )
    referral_fee_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total referral fee amount for this item (calculated)"
    )
    store_revenue = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Net revenue for store after referral fee (subtotal - referral_fee_amount)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'order_items'
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'
    
    def __str__(self):
        return f"{self.order.order_number} - {self.product_name} x{self.quantity}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate subtotal
        if not self.subtotal:
            self.subtotal = self.price * self.quantity
        
        # Auto-calculate store revenue if referral fee is set
        if self.referral_fee_amount > 0:
            self.store_revenue = self.subtotal - self.referral_fee_amount
        elif self.subtotal > 0:
            # If no fee, store gets full amount
            self.store_revenue = self.subtotal
        
        super().save(*args, **kwargs)
    
    @property
    def net_revenue(self):
        """Get net revenue for store (after fees)"""
        return self.store_revenue


class OrderStatusHistory(models.Model):
    """Track order status changes"""
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    status = models.CharField(max_length=20)
    notes = models.TextField(null=True, blank=True)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'order_status_history'
        verbose_name = 'Order Status History'
        verbose_name_plural = 'Order Status Histories'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.order.order_number} - {self.status}"


class Review(models.Model):
    """Product reviews"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews')
    
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=255, null=True, blank=True)
    comment = models.TextField()
    
    is_verified_purchase = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'reviews'
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'
        ordering = ['-created_at']
        unique_together = ['user', 'product', 'order']
    
    def __str__(self):
        return f"{self.user.phone} - {self.product.name} - {self.rating}★"


class ReviewImage(models.Model):
    """Review images uploaded by customers"""
    
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='orders/reviews/', null=True, blank=True)
    image_url = models.URLField(max_length=500, null=True, blank=True, help_text="Optional: External image URL (if not uploading a file)")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'review_images'
        verbose_name = 'Review Image'
        verbose_name_plural = 'Review Images'
    
    def __str__(self):
        return f"Review {self.review.id} - Image"
