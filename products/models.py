from django.db import models
from django.db.models import Q
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from users.models import User  # pyright: ignore[reportMissingImports]



class Currency(models.Model):
    """Currency model for multi-currency support"""
    
    code = models.CharField(max_length=3, unique=True, help_text="ISO 4217 currency code (e.g., USD, KGS, EUR)")
    name = models.CharField(max_length=100, help_text="Currency name (e.g., US Dollar, Kyrgyzstani Som)")
    symbol = models.CharField(max_length=10, help_text="Currency symbol (e.g., $, сом, €)")
    exchange_rate = models.DecimalField(
        max_digits=12, 
        decimal_places=6, 
        default=1.0,
        help_text="Exchange rate relative to base currency (USD). 1 USD = exchange_rate of this currency"
    )
    is_base = models.BooleanField(default=False, help_text="Is this the base currency?")
    is_active = models.BooleanField(default=True)
    market = models.CharField(
        max_length=3,
        choices=[
            ('KG', 'Kyrgyzstan'),
            ('US', 'United States'),
            ('ALL', 'All Markets'),
        ],
        default='ALL',
        help_text="Primary market for this currency"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'currencies'
        verbose_name = 'Currency'
        verbose_name_plural = 'Currencies'
        ordering = ['code']
        indexes = [
            models.Index(fields=['code', 'is_active']),
            models.Index(fields=['market', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.code} ({self.symbol}) - {self.name}"
    
    def clean(self):
        if self.is_base and self.exchange_rate != 1.0:
            raise ValidationError("Base currency must have exchange_rate = 1.0")
    
    def save(self, *args, **kwargs):
        self.full_clean()
        # Ensure only one base currency exists
        if self.is_base:
            Currency.objects.filter(is_base=True).exclude(pk=self.pk).update(is_base=False)
        super().save(*args, **kwargs)


class Category(models.Model):
    """Product categories"""
    
    MARKET_CHOICES = [
        ('KG', 'Kyrgyzstan'),
        ('US', 'United States'),
        ('ALL', 'All Markets'),
    ]
    
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, blank=True)
    market = models.CharField(max_length=3, choices=MARKET_CHOICES, default='ALL', db_index=True)
    description = models.TextField(null=True, blank=True)
    image = models.ImageField(upload_to='categories/', null=True, blank=True, help_text="Category image/icon")
    image_url = models.URLField(max_length=500, null=True, blank=True, help_text="Alternative: External image URL (if not uploading file)")
    icon = models.ImageField(upload_to='categories/icons/', null=True, blank=True, help_text="Category icon file (upload icon image)")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'categories'
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['sort_order', 'name']
        unique_together = ['name', 'market']  # Same category name can exist in different markets
        indexes = [
            models.Index(fields=['market', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.market})"
    
    def clean(self):
        """Validate category structure rules"""
        errors = {}
        
        # Rule: Cannot create subcategories if category has products directly (level 1 products)
        if self.pk:
            # Check if category has products without subcategory (level 1 products)
            has_level1_products = Product.objects.filter(
                category=self,
                subcategory__isnull=True
            ).exists()
            
            if has_level1_products:
                # Check if trying to add subcategories (this will be checked in Subcategory.clean)
                # But we can't check here since subcategories are created separately
                pass
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        self.full_clean()
        super().save(*args, **kwargs)


class Subcategory(models.Model):
    """Product subcategories - supports 2-level hierarchy"""
    
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    parent_subcategory = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='child_subcategories',
        null=True,
        blank=True,
        help_text="Parent subcategory for 3-level catalog structure. If set, this is a second-level subcategory."
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, blank=True)
    description = models.TextField(null=True, blank=True)
    image = models.ImageField(upload_to='categories/subcategories/', null=True, blank=True)
    image_url = models.URLField(max_length=500, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'subcategories'
        verbose_name = 'Subcategory'
        verbose_name_plural = 'Subcategories'
        ordering = ['sort_order', 'name']
        unique_together = [
            ['category', 'slug'],  # First-level subcategories (unique per category)
            ['parent_subcategory', 'slug'],  # Second-level subcategories (unique per parent)
        ]
        indexes = [
            models.Index(fields=['category', 'parent_subcategory', 'is_active']),
        ]
    
    def __str__(self):
        if self.parent_subcategory:
            return f"{self.category.name} -> {self.parent_subcategory.name} -> {self.name}"
        return f"{self.category.name} -> {self.name}"
    
    def clean(self):
        """Validate subcategory structure and uniqueness rules"""
        errors = {}
        
        # Validate that parent_subcategory belongs to the same category
        if self.parent_subcategory and self.parent_subcategory.category != self.category:
            errors['parent_subcategory'] = "Parent subcategory must belong to the same category."
        
        # Rule: Cannot create level 2 (subcategory) if category has products directly (level 1 products)
        # BUT: If category already has subcategories, allow creating more subcategories
        if not self.parent_subcategory and self.category:
            # Check if category has any existing subcategories
            category_has_subcategories = Subcategory.objects.filter(
                category=self.category,
                parent_subcategory__isnull=True
            ).exclude(pk=self.pk if self.pk else None).exists()
            
            # Only check for direct products if category doesn't already have subcategories
            # If category already has subcategories, it's fine to create more
            if not category_has_subcategories:
                # Check if category has products without subcategory (level 1 products)
                category_has_level1_products = Product.objects.filter(
                    category=self.category,
                    subcategory__isnull=True
                ).exists()
                if category_has_level1_products:
                    errors['category'] = (
                        f"Cannot create subcategory under '{self.category.name}' "
                        f"because it already has products directly assigned. "
                        f"Remove all products from the category before creating subcategories."
                    )
        
        # Rule: Cannot create subcategory_2 if subcategory_1 already has products directly
        # If subcategory_1 has products, it cannot have child subcategories (subcategory_2)
        # All products must be in subcategory_2, not in subcategory_1
        if self.parent_subcategory:
            # Check if parent subcategory_1 has products directly (without subcategory_2)
            parent_has_products = Product.objects.filter(
                subcategory=self.parent_subcategory,
                second_subcategory__isnull=True  # Products directly under subcategory_1
            ).exists()
            
            if parent_has_products:
                errors['parent_subcategory'] = (
                    f"Cannot create subcategory_2 under '{self.parent_subcategory.name}' "
                    f"because subcategory_1 already has products directly assigned. "
                    f"If subcategory_1 has products, it cannot have child subcategories (subcategory_2). "
                    f"Remove all products from subcategory_1 before creating subcategory_2, "
                    f"or move all products to subcategory_2."
                )
        
        # Validate uniqueness: Check if slug already exists at the same level
        if self.pk:  # Updating existing subcategory
            # Check for first-level subcategories (no parent)
            if not self.parent_subcategory:
                existing = Subcategory.objects.filter(
                    category=self.category,
                    slug=self.slug,
                    parent_subcategory__isnull=True
                ).exclude(pk=self.pk)
            else:
                # Check for second-level subcategories (with parent)
                existing = Subcategory.objects.filter(
                    parent_subcategory=self.parent_subcategory,
                    slug=self.slug
                ).exclude(pk=self.pk)
        else:  # Creating new subcategory
            # Check for first-level subcategories (no parent)
            if not self.parent_subcategory:
                existing = Subcategory.objects.filter(
                    category=self.category,
                    slug=self.slug,
                    parent_subcategory__isnull=True
                )
            else:
                # Check for second-level subcategories (with parent)
                existing = Subcategory.objects.filter(
                    parent_subcategory=self.parent_subcategory,
                    slug=self.slug
                )
        
        if existing.exists():
            if not self.parent_subcategory:
                errors['slug'] = f"A subcategory with slug '{self.slug}' already exists in category '{self.category.name}'."
            else:
                errors['slug'] = f"A child subcategory with slug '{self.slug}' already exists under '{self.parent_subcategory.name}'."
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def level(self):
        """Return the level of this subcategory (1 or 2)"""
        return 2 if self.parent_subcategory else 1


class Brand(models.Model):
    """Product brands"""
    
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    image = models.ImageField(upload_to='brands/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'brands'
        verbose_name = 'Brand'
        verbose_name_plural = 'Brands'
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # Handle slug uniqueness
            original_slug = self.slug
            counter = 1
            while Brand.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)


class Product(models.Model):
    """Products
    
    AI-Enhanced Product Model for intelligent recommendations.
    Supports LangGraph-based conversational product discovery.
    """
    
    MARKET_CHOICES = [
        ('KG', 'Kyrgyzstan'),
        ('US', 'United States'),
        ('ALL', 'All Markets'),  # Products available in all markets
    ]
    
    GENDER_CHOICES = [
        ('M', 'Men'),
        ('W', 'Women'),
        ('U', 'Unisex'),
        ('K', 'Kids'),
    ]
    
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    brand = models.ForeignKey(
        'Brand',
        on_delete=models.PROTECT,
        related_name='products',
        null=True,
        blank=True,
        help_text="Product brand"
    )
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.CASCADE,
        related_name='products',
        null=True,
        blank=True,
        help_text="Store that sells this product (for marketplace)"
    )
    description = models.TextField(null=True, blank=True)
    
    # Market
    market = models.CharField(max_length=3, choices=MARKET_CHOICES, default='KG', db_index=True)
    
    # Categorization - Flexible 3-level catalog structure
    # Level 1: category only
    # Level 2: category + subcategory (first level)
    # Level 3: category + subcategory (first level) + second_subcategory (second level)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    subcategory = models.ForeignKey(
        Subcategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        help_text="First-level subcategory. Required for level 2 and 3 catalog."
    )
    second_subcategory = models.ForeignKey(
        Subcategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='second_level_products',
        help_text="Second-level subcategory. Required only for level 3 catalog."
    )
    
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])  # Percentage
    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name='products',
        null=True,
        blank=True,
        help_text="Currency for this product's price. If not set, uses market default."
    )
    
    # Images
    image = models.ImageField(upload_to='products/main/', null=True, blank=True)  # Main image
    
    # Ratings and reviews
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    reviews_count = models.IntegerField(default=0)
    
    # Sales
    sales_count = models.IntegerField(default=0)
    
    # Stock
    in_stock = models.BooleanField(default=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_best_seller = models.BooleanField(default=False)
    
    # ==========================================
    # AI-POWERED RECOMMENDATION FIELDS
    # ==========================================
    
    # Enhanced description for AI understanding
    ai_description = models.TextField(
        null=True, 
        blank=True,
        help_text="Detailed description for AI to understand product better"
    )
    
    # Target audience
    gender = models.CharField(
        max_length=1, 
        choices=GENDER_CHOICES, 
        default='U',
        help_text="Target gender"
    )
    
    # JSON fields for AI matching (stored as JSON)
    # Style tags: casual, formal, sporty, elegant, trendy, classic, etc.
    style_tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Style attributes: ['casual', 'trendy', 'modern']"
    )
    
    # Occasion tags: party, work, wedding, casual, date, gym, beach, etc.
    occasion_tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Suitable occasions: ['party', 'night_out', 'clubbing']"
    )
    
    # Season tags: summer, winter, spring, fall, all-season
    season_tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Suitable seasons: ['summer', 'spring', 'all-season']"
    )
    
    # Color palette: primary colors in the product
    color_tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Colors: ['black', 'blue', 'white']"
    )
    
    # Material tags: cotton, silk, leather, denim, etc.
    material_tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Materials: ['cotton', 'polyester', 'breathable']"
    )
    
    # Age group tags: teens, young_adults, adults, seniors
    age_group_tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Age groups: ['young_adults', 'adults']"
    )
    
    # Activity tags: active, loungewear, office, outdoor, etc.
    activity_tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Activities: ['dancing', 'socializing', 'partying']"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'products'
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['market', 'is_active', 'in_stock']),  # Main filtering index
            models.Index(fields=['category', 'subcategory', 'second_subcategory']),
            models.Index(fields=['is_active', 'in_stock']),
            models.Index(fields=['-sales_count']),
            models.Index(fields=['gender', 'market']),  # For AI gender-based filtering
            models.Index(fields=['store', 'is_active']),  # For store filtering
        ]
    
    def __str__(self):
        brand_name = self.brand.name if self.brand else "No Brand"
        return f"{brand_name} - {self.name}"
    
    def get_currency(self):
        """Get currency for this product, falling back to market default"""
        if self.currency:
            return self.currency
        # Get default currency for market
        try:
            if self.market == 'US':
                return Currency.objects.filter(code='USD', is_active=True).first()
            elif self.market == 'KG':
                return Currency.objects.filter(code='KGS', is_active=True).first()
            else:
                # For ALL market, try to get base currency
                return Currency.objects.filter(is_base=True, is_active=True).first()
        except Currency.DoesNotExist:
            return None
    
    def clean(self):
        """Validate catalog structure consistency"""
        errors = {}
        
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
        
        # Rule: Cannot add products directly to category (level 1) if it has subcategories (level 2)
        if not self.subcategory and self.category:
            # Check if category has subcategories
            has_subcategories = self.category.subcategories.filter(
                parent_subcategory__isnull=True
            ).exists()
            
            if has_subcategories:
                errors['category'] = (
                    f"Cannot add products directly to category '{self.category.name}' "
                    f"because it already has subcategories. "
                    f"Either remove the subcategories or assign this product to one of them."
                )
        
        # Rule: Cannot add products to subcategory_1 if it has child subcategories (subcategory_2)
        # If subcategory_1 has subcategory_2 children, all products must be in subcategory_2, not subcategory_1
        if self.subcategory and not self.second_subcategory:
            # Check if this subcategory_1 has child subcategories (subcategory_2)
            has_children = self.subcategory.child_subcategories.exists()
            if has_children:
                child_names = list(self.subcategory.child_subcategories.values_list('name', flat=True))
                errors['subcategory'] = (
                    f"Cannot add products directly to subcategory_1 '{self.subcategory.name}' "
                    f"because it has child subcategories (subcategory_2): {', '.join(child_names)}. "
                    f"Subcategory_1 is just a branch for subcategory_2. "
                    f"All products must be assigned to one of the subcategory_2 options, not to subcategory_1."
                )
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            brand_part = self.brand.slug if self.brand else "product"
            base_slug = slugify(f"{brand_part}-{self.name}")
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
        
        # Auto-sync to Pinecone after save (async in background)
        try:
            from ai_assistant.pinecone_utils import sync_product_to_pinecone  # pyright: ignore[reportMissingImports]
            sync_product_to_pinecone(self)
        except Exception as e:
            # Log error but don't block the save
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to sync product {self.id} to Pinecone: {str(e)}")
    
    def get_ai_context(self):
        """
        Get product information formatted for AI understanding
        Used by LangGraph agents to understand product details
        """
        return {
            'id': self.id,
            'name': self.name,
            'brand': self.brand.name if self.brand else None,
            'description': self.ai_description or self.description,
            'price': float(self.price),
            'category': self.category.name,
            'subcategory': self.subcategory.name if self.subcategory else None,
            'gender': self.get_gender_display(),
            'style': self.style_tags,
            'occasions': self.occasion_tags,
            'seasons': self.season_tags,
            'colors': self.color_tags,
            'materials': self.material_tags,
            'age_groups': self.age_group_tags,
            'activities': self.activity_tags,
            'rating': float(self.rating),
            'in_stock': self.in_stock,
            'image': self.image,
            'market': self.market,
        }
    
    @classmethod
    def search_for_ai(cls, query_params):
        """
        Search products based on AI-extracted parameters
        
        Args:
            query_params: dict with keys like:
                - market: str
                - gender: str
                - occasion: list
                - style: list
                - season: list
                - colors: list
                - price_min: float
                - price_max: float
        
        Returns:
            QuerySet of matching products
        """
        queryset = cls.objects.filter(is_active=True, in_stock=True)
        
        # Market filter
        if 'market' in query_params:
            market = query_params['market']
            queryset = queryset.filter(Q(market=market) | Q(market='ALL'))
        
        # Gender filter
        if 'gender' in query_params:
            gender = query_params['gender']
            queryset = queryset.filter(Q(gender=gender) | Q(gender='U'))
        
        # Occasion filter
        if 'occasion' in query_params and query_params['occasion']:
            occasions = query_params['occasion']
            # Match if product has ANY of the specified occasions
            occasion_query = Q()
            for occ in occasions:
                occasion_query |= Q(occasion_tags__contains=[occ])
            queryset = queryset.filter(occasion_query)
        
        # Style filter
        if 'style' in query_params and query_params['style']:
            styles = query_params['style']
            style_query = Q()
            for style in styles:
                style_query |= Q(style_tags__contains=[style])
            queryset = queryset.filter(style_query)
        
        # Season filter
        if 'season' in query_params and query_params['season']:
            seasons = query_params['season']
            season_query = Q()
            for season in seasons:
                season_query |= Q(season_tags__contains=[season])
            queryset = queryset.filter(season_query)
        
        # Color filter
        if 'colors' in query_params and query_params['colors']:
            colors = query_params['colors']
            color_query = Q()
            for color in colors:
                color_query |= Q(color_tags__contains=[color])
            queryset = queryset.filter(color_query)
        
        # Price range
        if 'price_min' in query_params:
            queryset = queryset.filter(price__gte=query_params['price_min'])
        if 'price_max' in query_params:
            queryset = queryset.filter(price__lte=query_params['price_max'])
        
        # Order by relevance (rating, sales, featured)
        queryset = queryset.order_by('-is_featured', '-rating', '-sales_count')
        
        return queryset


class ProductImage(models.Model):
    """Additional product images"""
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/gallery/', null=True, blank=True)
    alt_text = models.CharField(max_length=255, null=True, blank=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'product_images'
        verbose_name = 'Product Image'
        verbose_name_plural = 'Product Images'
        ordering = ['sort_order', 'created_at']
    
    def __str__(self):
        return f"{self.product.name} - Image {self.sort_order}"


class ProductFeature(models.Model):
    """Product features/specifications"""
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='features')
    feature_text = models.CharField(max_length=500)
    sort_order = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'product_features'
        verbose_name = 'Product Feature'
        verbose_name_plural = 'Product Features'
        ordering = ['sort_order']
    
    def __str__(self):
        return f"{self.product.name} - {self.feature_text[:50]}"  # type: ignore


class ProductSizeOption(models.Model):
    """Declarative list of sizes available for a product."""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='size_options',
    )
    name = models.CharField(max_length=50)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'product_size_options'
        verbose_name = 'Product Size'
        verbose_name_plural = 'Product Sizes'
        ordering = ['product', 'sort_order', 'name']
        unique_together = ('product', 'name')

    def __str__(self):
        return f"{self.product.name} • {self.name}"


class ProductColorOption(models.Model):
    """Color choices scoped to a specific size."""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='color_options',
    )
    size = models.ForeignKey(
        ProductSizeOption,
        on_delete=models.CASCADE,
        related_name='color_options',
    )
    name = models.CharField(max_length=50)
    hex_code = models.CharField(
        max_length=7,
        null=True,
        blank=True,
        help_text="HEX code (#FFFFFF).",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'product_color_options'
        verbose_name = 'Product Color'
        verbose_name_plural = 'Product Colors'
        ordering = ['product', 'size__sort_order', 'size__name', 'name']
        unique_together = ('product', 'size', 'name')

    def __str__(self):
        return f"{self.product.name} • {self.size.name} • {self.name}"

    def clean(self):
        if self.size and self.product and self.size.product_id != self.product_id:
            raise ValidationError("Selected size does not belong to this product.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class SKU(models.Model):
    """Product SKUs (Stock Keeping Units) - Product variants"""
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='skus')
    sku_code = models.CharField(max_length=100, unique=True)
    
    # Variant attributes
    size_option = models.ForeignKey(
        ProductSizeOption,
        on_delete=models.CASCADE,
        related_name='skus',
        null=True,
        blank=True,
    )
    color_option = models.ForeignKey(
        ProductColorOption,
        on_delete=models.CASCADE,
        related_name='skus',
        null=True,
        blank=True,
    )
    
    # Pricing (can override product price)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name='skus',
        null=True,
        blank=True,
        help_text="Currency for this SKU's price. If not set, uses product currency."
    )
    
    # Stock
    stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    
    # Variant image
    variant_image = models.ImageField(upload_to='products/variants/', null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'skus'
        verbose_name = 'SKU'
        verbose_name_plural = 'SKUs'
        ordering = ['product', 'size_option__sort_order', 'size_option__name', 'color_option__name']
        unique_together = ['product', 'size_option', 'color_option']
        indexes = [
            models.Index(fields=['sku_code']),
            models.Index(fields=['product', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.product.name} - {self.size} / {self.color}"
    
    def get_currency(self):
        """Get currency for this SKU, falling back to product currency"""
        if self.currency:
            return self.currency
        return self.product.get_currency()
    
    def clean(self):
        errors = {}
        if self.size_option and self.size_option.product_id != self.product_id:
            errors['size_option'] = "Selected size does not belong to this product."
        if self.color_option:
            if self.color_option.product_id != self.product_id:
                errors['color_option'] = "Selected color does not belong to this product."
            elif self.color_option.size_id != getattr(self.size_option, 'id', None):
                errors['color_option'] = "Selected color is not available for the chosen size."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.sku_code:
            # Auto-generate SKU code
            base_code = f"{self.product.slug[:20]}-{self.size}-{self.color}".upper().replace(' ', '-')
            self.sku_code = base_code
        super().save(*args, **kwargs)

    @property
    def size(self):
        return self.size_option.name if self.size_option else None

    @property
    def color(self):
        return self.color_option.name if self.color_option else None


class Cart(models.Model):
    """Shopping cart"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'carts'
        verbose_name = 'Cart'
        verbose_name_plural = 'Carts'
    
    def __str__(self):
        return f"Cart - {self.user.phone}"
    
    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())
    
    @property
    def total_price(self):
        return sum(item.subtotal for item in self.items.all())


class CartItem(models.Model):
    """Cart items"""
    
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    sku = models.ForeignKey(SKU, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cart_items'
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'
        unique_together = ['cart', 'sku']
    
    def __str__(self):
        return f"{self.cart.user.phone} - {self.sku.product.name} x{self.quantity}"
    
    @property
    def subtotal(self):
        return self.sku.price * self.quantity


class Wishlist(models.Model):
    """User wishlist"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wishlist')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'wishlists'
        verbose_name = 'Wishlist'
        verbose_name_plural = 'Wishlists'
    
    def __str__(self):
        return f"Wishlist - {self.user.phone}"


class WishlistItem(models.Model):
    """Wishlist items"""
    
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'wishlist_items'
        verbose_name = 'Wishlist Item'
        verbose_name_plural = 'Wishlist Items'
        unique_together = ['wishlist', 'product']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.wishlist.user.phone} - {self.product.name}"
