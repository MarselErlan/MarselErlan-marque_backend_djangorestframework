"""
Referral Fee models for marketplace fee management.
Fees are charged based on product category structure.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal


class ReferralFee(models.Model):
    """Referral fee configuration based on product category structure.
    
    Supports 3-level fee matching:
    - Level 1: Category only (applies to all products in category)
    - Level 2: Category + Subcategory (applies to products in specific subcategory)
    - Level 3: Category + Subcategory + Second Subcategory (most specific)
    
    More specific fees take precedence over general ones.
    """
    
    # Category relationships - supports flexible 3-level catalog
    category = models.ForeignKey(
        'products.Category',
        on_delete=models.CASCADE,
        related_name='referral_fees',
        help_text="Category for this fee (required)"
    )
    
    subcategory = models.ForeignKey(
        'products.Subcategory',
        on_delete=models.CASCADE,
        related_name='referral_fees',
        null=True,
        blank=True,
        help_text="First-level subcategory (optional, for more specific fee)"
    )
    
    second_subcategory = models.ForeignKey(
        'products.Subcategory',
        on_delete=models.CASCADE,
        related_name='second_level_referral_fees',
        null=True,
        blank=True,
        help_text="Second-level subcategory (optional, most specific fee)"
    )
    
    # Fee configuration
    fee_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="Fee percentage (0-100%)"
    )
    
    fee_fixed = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Fixed fee amount (in addition to percentage)"
    )
    
    # Status
    is_active = models.BooleanField(default=True, help_text="Is this fee configuration active?")
    
    # Metadata
    description = models.TextField(
        null=True,
        blank=True,
        help_text="Description of this fee configuration"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'referral_fees'
        verbose_name = 'Referral Fee'
        verbose_name_plural = 'Referral Fees'
        ordering = ['category', 'subcategory', 'second_subcategory']
        indexes = [
            models.Index(fields=['category', 'subcategory', 'second_subcategory', 'is_active']),
            models.Index(fields=['category', 'is_active']),
        ]
    
    def __str__(self):
        parts = [self.category.name]
        if self.subcategory:
            parts.append(self.subcategory.name)
        if self.second_subcategory:
            parts.append(self.second_subcategory.name)
        fee_str = f"{self.fee_percentage}%"
        if self.fee_fixed > 0:
            fee_str += f" + {self.fee_fixed}"
        return f"{' -> '.join(parts)}: {fee_str}"
    
    def clean(self):
        """Validate fee configuration"""
        errors = {}
        
        # Category is required
        if not self.category:
            errors['category'] = "Category is required."
        
        # If second_subcategory is set, subcategory must also be set
        if self.second_subcategory and not self.subcategory:
            errors['second_subcategory'] = "Cannot set second_subcategory without first-level subcategory."
        
        # If second_subcategory is set, it must be a child of subcategory
        if self.second_subcategory and self.subcategory:
            if self.second_subcategory.parent_subcategory != self.subcategory:
                errors['second_subcategory'] = "Second subcategory must be a child of the first subcategory."
        
        # Ensure all subcategories belong to the same category
        if self.subcategory and self.subcategory.category != self.category:
            errors['subcategory'] = "Subcategory must belong to the same category."
        
        if self.second_subcategory and self.second_subcategory.category != self.category:
            errors['second_subcategory'] = "Second subcategory must belong to the same category."
        
        # Ensure subcategory is first-level (no parent) if set
        if self.subcategory and self.subcategory.parent_subcategory:
            errors['subcategory'] = "Subcategory must be a first-level subcategory (no parent)."
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Validate before saving"""
        self.full_clean()
        super().save(*args, **kwargs)
    
    @classmethod
    def get_fee_for_product(cls, product):
        """Get the most specific referral fee for a product.
        
        Matching priority (most specific first):
        1. Category + Subcategory + Second Subcategory
        2. Category + Subcategory
        3. Category only
        
        Args:
            product: Product instance
            
        Returns:
            ReferralFee instance or None if no matching fee found
        """
        if not product or not product.category:
            return None
        
        # Try most specific match first: category + subcategory + second_subcategory
        if product.second_subcategory and product.subcategory:
            fee = cls.objects.filter(
                category=product.category,
                subcategory=product.subcategory,
                second_subcategory=product.second_subcategory,
                is_active=True
            ).first()
            if fee:
                return fee
        
        # Try category + subcategory
        if product.subcategory:
            fee = cls.objects.filter(
                category=product.category,
                subcategory=product.subcategory,
                second_subcategory__isnull=True,
                is_active=True
            ).first()
            if fee:
                return fee
        
        # Try category only
        fee = cls.objects.filter(
            category=product.category,
            subcategory__isnull=True,
            second_subcategory__isnull=True,
            is_active=True
        ).first()
        
        return fee
    
    def calculate_fee(self, order_amount):
        """Calculate fee amount for a given order amount.
        
        Args:
            order_amount: Decimal amount of the order
            
        Returns:
            Decimal: Total fee amount (percentage + fixed)
        """
        percentage_fee = (order_amount * self.fee_percentage) / Decimal('100.00')
        total_fee = percentage_fee + self.fee_fixed
        return total_fee
