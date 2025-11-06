from django.db import models
from django.core.validators import MinValueValidator


class Banner(models.Model):
    """Homepage banners"""
    
    BANNER_TYPE_CHOICES = [
        ('hero', 'Hero Banner'),
        ('promo', 'Promo Banner'),
        ('category', 'Category Banner'),
    ]
    
    MARKET_CHOICES = [
        ('KG', 'Kyrgyzstan'),
        ('US', 'United States'),
        ('ALL', 'All Markets'),
    ]
    
    # Content
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=500, null=True, blank=True)
    image_url = models.URLField(max_length=500)
    
    # Type & Market
    banner_type = models.CharField(max_length=20, choices=BANNER_TYPE_CHOICES, default='hero', db_index=True)
    market = models.CharField(max_length=3, choices=MARKET_CHOICES, default='ALL', db_index=True)
    
    # Call to action
    button_text = models.CharField(max_length=100, null=True, blank=True)
    link_url = models.URLField(max_length=500, null=True, blank=True)
    
    # Display settings
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    
    # Scheduling (optional)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    
    # Analytics
    view_count = models.IntegerField(default=0)
    click_count = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'banners'
        verbose_name = 'Banner'
        verbose_name_plural = 'Banners'
        ordering = ['sort_order', '-created_at']
        indexes = [
            models.Index(fields=['market', 'banner_type', 'is_active']),
            models.Index(fields=['banner_type', 'is_active']),
            models.Index(fields=['sort_order']),
        ]
    
    def __str__(self):
        return f"{self.get_banner_type_display()} - {self.title}"
    
    @property
    def ctr(self):
        """Click-through rate"""
        if self.view_count > 0:
            return (self.click_count / self.view_count) * 100
        return 0
