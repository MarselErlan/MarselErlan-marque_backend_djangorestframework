"""
Store models for multi-store marketplace.
"""

from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from users.models import User


class Store(models.Model):
    """
    Store model for marketplace - represents a business/seller on the platform.
    
    Each store can have multiple products. Users can browse stores and their products.
    """
    
    MARKET_CHOICES = [
        ('KG', 'Kyrgyzstan'),
        ('US', 'United States'),
        ('ALL', 'All Markets'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('closed', 'Closed'),
    ]
    
    # Basic Information
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    description = models.TextField(null=True, blank=True)
    
    # Owner (business owner who manages this store)
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='owned_stores',
        help_text="Business owner who manages this store"
    )
    
    # Market
    market = models.CharField(
        max_length=3,
        choices=MARKET_CHOICES,
        default='KG',
        db_index=True,
        help_text="Primary market for this store"
    )
    
    # Visual Identity
    logo = models.ImageField(
        upload_to='stores/logos/',
        null=True,
        blank=True,
        help_text="Store logo image"
    )
    logo_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Alternative: External logo URL"
    )
    cover_image = models.ImageField(
        upload_to='stores/covers/',
        null=True,
        blank=True,
        help_text="Store cover/banner image"
    )
    cover_image_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Alternative: External cover image URL"
    )
    
    # Contact Information
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    website = models.URLField(max_length=500, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    
    # Statistics (cached for performance)
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Average rating from reviews"
    )
    reviews_count = models.IntegerField(default=0, help_text="Total number of reviews")
    orders_count = models.IntegerField(default=0, help_text="Total number of orders")
    products_count = models.IntegerField(default=0, help_text="Total number of active products")
    likes_count = models.IntegerField(default=0, help_text="Total number of likes/followers")
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    is_active = models.BooleanField(default=True, db_index=True)
    is_verified = models.BooleanField(
        default=False,
        help_text="Verified store badge (admin approved)"
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="Featured store (shown prominently)"
    )
    
    # Contract/Agreement
    contract_signed_date = models.DateTimeField(null=True, blank=True)
    contract_expiry_date = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'stores'
        verbose_name = 'Store'
        verbose_name_plural = 'Stores'
        ordering = ['-is_featured', '-rating', '-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['market', 'is_active', 'status']),
            models.Index(fields=['owner', 'is_active']),
            models.Index(fields=['is_featured', '-rating']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Store.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
    
    def update_statistics(self):
        """Update cached statistics from related models."""
        from products.models import Product
        from orders.models import Order, Review
        
        # Update products count
        self.products_count = Product.objects.filter(
            store=self,
            is_active=True
        ).count()
        
        # Update orders count (orders with products from this store)
        self.orders_count = Order.objects.filter(
            items__sku__product__store=self
        ).distinct().count()
        
        # Update reviews count and rating
        reviews = Review.objects.filter(product__store=self)
        self.reviews_count = reviews.count()
        if self.reviews_count > 0:
            from django.db.models import Avg
            avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
            self.rating = round(avg_rating, 2) if avg_rating else 0.0
        else:
            self.rating = 0.0
        
        # Update likes count (from store followers/likes - can be implemented later)
        # For now, we'll keep it at 0 or implement a StoreLike model
        
        self.save(update_fields=['products_count', 'orders_count', 'reviews_count', 'rating'])


class StoreFollower(models.Model):
    """
    Store followers/likes - users who follow/subscribe to a store.
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='followed_stores'
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='followers'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'store_followers'
        verbose_name = 'Store Follower'
        verbose_name_plural = 'Store Followers'
        unique_together = ['user', 'store']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['store', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.phone} follows {self.store.name}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update store likes count
        self.store.likes_count = self.store.followers.count()
        self.store.save(update_fields=['likes_count'])
    
    def delete(self, *args, **kwargs):
        store = self.store
        super().delete(*args, **kwargs)
        # Update store likes count
        store.likes_count = store.followers.count()
        store.save(update_fields=['likes_count'])
