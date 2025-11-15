"""
Serializers for the products app.

These serializers expose product catalog data in a format that matches
the requirements of the Next.js storefront (see `marque_frontend`).
"""

from collections import OrderedDict
from typing import Dict, Iterable, List, Optional

from django.utils.text import slugify
from rest_framework import serializers

from orders.models import Review
from .models import (
    Cart,
    CartItem,
    Category,
    Product,
    ProductFeature,
    ProductImage,
    SKU,
    Subcategory,
    Wishlist,
    WishlistItem,
)


class CategorySummarySerializer(serializers.ModelSerializer):
    """Lightweight representation of a category."""

    class Meta:
        model = Category
        fields = ("id", "name", "slug")


class SubcategorySummarySerializer(serializers.ModelSerializer):
    """Lightweight representation of a subcategory."""

    class Meta:
        model = Subcategory
        fields = ("id", "name", "slug")


class CategoryListSerializer(CategorySummarySerializer):
    """Full representation of a category for catalog listings."""

    product_count = serializers.IntegerField(read_only=True)

    class Meta(CategorySummarySerializer.Meta):
        fields = CategorySummarySerializer.Meta.fields + (
            "description",
            "image_url",
            "icon",
            "is_active",
            "market",
            "sort_order",
            "product_count",
        )


class SubcategoryListSerializer(SubcategorySummarySerializer):
    """Full representation of a subcategory for catalog listings."""

    product_count = serializers.IntegerField(read_only=True)

    class Meta(SubcategorySummarySerializer.Meta):
        fields = SubcategorySummarySerializer.Meta.fields + (
            "description",
            "image_url",
            "is_active",
            "sort_order",
            "product_count",
        )


class CategoryDetailSerializer(CategoryListSerializer):
    """Detailed category representation."""

    pass


class ImageUploadSerializer(serializers.Serializer):
    """Serializer for validating image uploads."""

    image = serializers.ImageField()
    folder = serializers.CharField(required=False, allow_blank=True)


class ProductImageSerializer(serializers.ModelSerializer):
    """Additional images for a product."""

    url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ("id", "url", "alt_text", "sort_order")

    def get_url(self, obj: ProductImage) -> Optional[str]:
        if not obj.image:
            return None
        request = self.context.get("request") if hasattr(self, "context") else None
        url = obj.image.url
        if request:
            return request.build_absolute_uri(url)
        return url


class SKUSerializer(serializers.ModelSerializer):
    """Serializer for product variants (Size/Color combinations)."""

    size = serializers.CharField(source="size_option.name", read_only=True)
    color = serializers.CharField(source="color_option.name", read_only=True)
    color_hex = serializers.CharField(source="color_option.hex_code", read_only=True)
    size_option_id = serializers.IntegerField(source="size_option.id", read_only=True)
    color_option_id = serializers.IntegerField(source="color_option.id", read_only=True)
    price = serializers.SerializerMethodField()
    original_price = serializers.SerializerMethodField()
    variant_image = serializers.SerializerMethodField()

    class Meta:
        model = SKU
        fields = (
            "id",
            "sku_code",
            "size",
            "size_option_id",
            "color",
            "color_option_id",
            "color_hex",
            "price",
            "original_price",
            "stock",
            "variant_image",
            "is_active",
        )

    @staticmethod
    def _decimal_to_float(value):
        return float(value) if value is not None else None

    def get_price(self, obj: SKU) -> Optional[float]:
        return self._decimal_to_float(obj.price)

    def get_original_price(self, obj: SKU) -> Optional[float]:
        return self._decimal_to_float(obj.original_price)

    def get_variant_image(self, obj: SKU) -> Optional[str]:
        if not obj.variant_image:
            return None
        request = self.context.get("request") if hasattr(self, "context") else None
        url = obj.variant_image.url
        return request.build_absolute_uri(url) if request else url


class ProductSerializerMixin:
    """Shared helpers for product serializers."""

    @staticmethod
    def _active_skus(obj: Product) -> List[SKU]:
        if not hasattr(obj, "_prefetched_objects_cache"):
            # No prefetch -> evaluate queryset each time (small datasets only)
            skus = list(obj.skus.filter(is_active=True))
        else:
            skus = [
                sku for sku in obj.skus.all()
                if getattr(sku, "is_active", True)
            ]

        if not skus:
            if hasattr(obj, "_prefetched_objects_cache"):
                skus = list(obj.skus.all())
            else:
                skus = list(obj.skus.all())
        return skus

    @staticmethod
    def _decimal_list_to_float(values: Iterable) -> List[float]:
        return [float(value) for value in values if value is not None]

    def _price_range(self, obj: Product) -> Dict[str, Optional[float]]:
        skus = self._active_skus(obj)
        sku_prices = [float(sku.price) for sku in skus if sku.price is not None]
        sku_originals = [
            float(sku.original_price) for sku in skus if sku.original_price is not None
        ]

        price_min = min(sku_prices) if sku_prices else float(obj.price)
        price_max = max(sku_prices) if sku_prices else float(obj.price)

        original_price_min = min(sku_originals) if sku_originals else (
            float(obj.original_price) if obj.original_price else None
        )
        original_price_max = max(sku_originals) if sku_originals else (
            float(obj.original_price) if obj.original_price else None
        )

        return {
            "price_min": price_min,
            "price_max": price_max,
            "original_price_min": original_price_min,
            "original_price_max": original_price_max,
        }

    def _available_sizes(self, obj: Product) -> List[str]:
        skus = self._active_skus(obj)
        sizes = {sku.size for sku in skus if sku.size}
        return sorted(sizes)

    def _available_colors(self, obj: Product) -> List[str]:
        skus = self._active_skus(obj)
        colors = {sku.color for sku in skus if sku.color}
        return sorted(colors)

    @staticmethod
    def _brand_payload(obj: Product) -> Dict[str, Optional[str]]:
        brand_slug = slugify(obj.brand) if obj.brand else None
        return {
            "name": obj.brand,
            "slug": brand_slug,
        }

    def _build_absolute_uri(self, path: Optional[str]) -> Optional[str]:
        if not path:
            return None
        request = self.context.get("request") if hasattr(self, "context") else None
        return request.build_absolute_uri(path) if request else path

    def _primary_image(self, obj: Product) -> Optional[str]:
        if obj.image:
            return self._build_absolute_uri(obj.image.url)
        first_image = obj.images.first()
        if first_image and first_image.image:
            return self._build_absolute_uri(first_image.image.url)
        return None

    def _product_summary(self, obj: Product) -> Dict[str, Optional[str]]:
        payload = {
            "id": obj.id,
            "title": obj.name,
            "name": obj.name,
            "brand": self._brand_payload(obj),
            "price_min": None,
            "price_max": None,
            "original_price_min": None,
            "original_price_max": None,
            "discount_percent": obj.discount,
            "image": self._primary_image(obj),
            "images": [],
            "category": CategorySummarySerializer(obj.category).data if obj.category else None,
            "subcategory": SubcategorySummarySerializer(obj.subcategory).data if obj.subcategory else None,
            "available_sizes": self._available_sizes(obj),
            "available_colors": self._available_colors(obj),
            "rating_avg": float(obj.rating or 0.0),
            "rating_count": obj.reviews_count,
            "sold_count": obj.sales_count,
            "in_stock": obj.in_stock,
            "description": obj.description,
        }

        if obj.images.exists():
            payload["images"] = [
                self._build_absolute_uri(image.image.url)
                for image in obj.images.all()
                if image.image
            ]

        price_payload = self._price_range(obj)
        payload["price_min"] = price_payload["price_min"]
        payload["price_max"] = price_payload["price_max"]
        payload["original_price_min"] = price_payload["original_price_min"]
        payload["original_price_max"] = price_payload["original_price_max"]
        return payload


class ProductListSerializer(ProductSerializerMixin, serializers.ModelSerializer):
    """
    Serializer for product listing (home, category, search, similar products).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._price_cache = {}

    title = serializers.CharField(source="name")
    brand = serializers.SerializerMethodField()
    brand_name = serializers.CharField(source="brand", read_only=True)
    image = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    price_min = serializers.SerializerMethodField()
    price_max = serializers.SerializerMethodField()
    original_price = serializers.SerializerMethodField()
    original_price_min = serializers.SerializerMethodField()
    original_price_max = serializers.SerializerMethodField()
    discount = serializers.IntegerField()
    rating_avg = serializers.SerializerMethodField()
    rating_count = serializers.IntegerField(source="reviews_count")
    sold_count = serializers.IntegerField(source="sales_count")
    available_sizes = serializers.SerializerMethodField()
    available_colors = serializers.SerializerMethodField()
    category = CategorySummarySerializer(read_only=True)
    subcategory = SubcategorySummarySerializer(read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "slug",
            "title",
            "description",
            "brand",
            "brand_name",
            "image",
            "price",
            "price_min",
            "price_max",
            "original_price",
            "original_price_min",
            "original_price_max",
            "discount",
            "rating_avg",
            "rating_count",
            "sold_count",
            "available_sizes",
            "available_colors",
            "category",
            "subcategory",
            "market",
            "is_featured",
            "is_best_seller",
        )

    def get_brand(self, obj: Product) -> Dict[str, Optional[str]]:
        return self._brand_payload(obj)

    def get_image(self, obj: Product) -> Optional[str]:
        if not obj.image:
            return None
        return self._build_absolute_uri(obj.image.url)

    def _price_payload(self, obj: Product) -> Dict[str, Optional[float]]:
        cache_key = obj.pk or id(obj)
        if cache_key not in self._price_cache:
            self._price_cache[cache_key] = self._price_range(obj)
        return self._price_cache[cache_key]

    def get_price(self, obj: Product) -> float:
        return self._price_payload(obj)["price_min"]

    def get_price_min(self, obj: Product) -> float:
        return self._price_payload(obj)["price_min"]

    def get_price_max(self, obj: Product) -> float:
        return self._price_payload(obj)["price_max"]

    def get_original_price(self, obj: Product) -> Optional[float]:
        payload = self._price_payload(obj)
        return payload["original_price_min"] or payload["price_min"]

    def get_original_price_min(self, obj: Product) -> Optional[float]:
        return self._price_payload(obj)["original_price_min"]

    def get_original_price_max(self, obj: Product) -> Optional[float]:
        return self._price_payload(obj)["original_price_max"]

    @staticmethod
    def get_rating_avg(obj: Product) -> float:
        return float(obj.rating or 0.0)

    def get_available_sizes(self, obj: Product) -> List[str]:
        return self._available_sizes(obj)

    def get_available_colors(self, obj: Product) -> List[str]:
        return self._available_colors(obj)


class ReviewSerializer(serializers.ModelSerializer):
    """Approved reviews for a product."""

    user_name = serializers.SerializerMethodField()
    text = serializers.CharField(source="comment")

    class Meta:
        model = Review
        fields = (
            "id",
            "rating",
            "title",
            "text",
            "is_verified_purchase",
            "created_at",
            "user_name",
        )

    @staticmethod
    def get_user_name(obj: Review) -> str:
        if obj.user and obj.user.full_name:
            return obj.user.full_name
        if obj.user and obj.user.phone:
            return obj.user.phone
        return "Покупатель"


class ProductDetailSerializer(ProductListSerializer):
    """Detailed representation of a single product."""

    images = ProductImageSerializer(many=True, read_only=True)
    skus = serializers.SerializerMethodField()
    attributes = serializers.SerializerMethodField()
    features = serializers.SerializerMethodField()
    available_sizes = serializers.SerializerMethodField()
    available_colors = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()
    similar_products = serializers.SerializerMethodField()

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + (
            "ai_description",
            "in_stock",
            "images",
            "skus",
            "attributes",
            "features",
            "available_sizes",
            "available_colors",
            "reviews",
            "similar_products",
        )

    def get_skus(self, obj: Product) -> List[OrderedDict]:
        serializer = SKUSerializer(
            self._active_skus(obj),
            many=True,
            context=self.context,
        )
        return serializer.data

    def get_features(self, obj: Product) -> List[str]:
        if hasattr(obj, "_prefetched_objects_cache"):
            features = list(obj.features.all())
        else:
            features = list(ProductFeature.objects.filter(product=obj))
        return [feature.feature_text for feature in features if feature.feature_text]

    def get_attributes(self, obj: Product) -> Dict[str, str]:
        attributes: Dict[str, str] = OrderedDict()
        # Parse structured "Key: Value" features
        if hasattr(obj, "_prefetched_objects_cache"):
            features_iterable = obj.features.all()
        else:
            features_iterable = ProductFeature.objects.filter(product=obj)

        for feature in features_iterable:
            text = feature.feature_text or ""
            if ":" in text:
                key, value = text.split(":", 1)
                attributes[key.strip()] = value.strip()

        # Ensure some core attributes are always present
        if obj.brand and "Бренд" not in attributes:
            attributes["Бренд"] = obj.brand
        if obj.category and obj.category.name and "Категория" not in attributes:
            attributes["Категория"] = obj.category.name
        if obj.subcategory and obj.subcategory.name and "Подкатегория" not in attributes:
            attributes["Подкатегория"] = obj.subcategory.name

        return attributes

    def get_reviews(self, obj: Product) -> List[OrderedDict]:
        queryset = obj.reviews.filter(is_approved=True).select_related("user")
        serializer = ReviewSerializer(queryset, many=True)
        return serializer.data

    def get_similar_products(self, obj: Product) -> List[OrderedDict]:
        request = self.context.get("request")
        queryset = Product.objects.filter(
            is_active=True,
            in_stock=True,
        ).exclude(id=obj.id)

        if obj.subcategory:
            queryset = queryset.filter(subcategory=obj.subcategory)
        elif obj.category:
            queryset = queryset.filter(category=obj.category)

        queryset = queryset.select_related("category", "subcategory").prefetch_related(
            "skus",
        ).order_by("-is_best_seller", "-rating", "-sales_count")[:8]

        serializer = ProductListSerializer(
            queryset,
            many=True,
            context={"request": request} if request else None,
        )
        return serializer.data


class CartItemSerializer(ProductSerializerMixin, serializers.ModelSerializer):
    """Serializer for individual cart items."""

    product_id = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    original_price = serializers.SerializerMethodField()
    brand = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    sku_id = serializers.IntegerField(source="sku.id", read_only=True)
    size = serializers.CharField(source="sku.size", read_only=True)
    color = serializers.CharField(source="sku.color", read_only=True)

    class Meta:
        model = CartItem
        fields = (
            "id",
            "product_id",
            "sku_id",
            "name",
            "price",
            "original_price",
            "brand",
            "image",
            "quantity",
            "size",
            "color",
        )

    def get_product_id(self, obj: CartItem) -> Optional[int]:
        return obj.sku.product_id if obj.sku else None

    def get_name(self, obj: CartItem) -> str:
        return obj.sku.product.name if obj.sku and obj.sku.product else ""

    def get_price(self, obj: CartItem) -> Optional[float]:
        if obj.sku and obj.sku.price is not None:
            return float(obj.sku.price)
        if obj.sku and obj.sku.product and obj.sku.product.price is not None:
            return float(obj.sku.product.price)
        return None

    def get_original_price(self, obj: CartItem) -> Optional[float]:
        if obj.sku and obj.sku.original_price is not None:
            return float(obj.sku.original_price)
        if obj.sku and obj.sku.product and obj.sku.product.original_price is not None:
            return float(obj.sku.product.original_price)
        return None

    def get_brand(self, obj: CartItem) -> Optional[str]:
        if obj.sku and obj.sku.product:
            return obj.sku.product.brand
        return None

    def get_image(self, obj: CartItem) -> Optional[str]:
        if obj.sku and obj.sku.variant_image:
            return self._build_absolute_uri(obj.sku.variant_image.url)
        if obj.sku and obj.sku.product:
            return self._primary_image(obj.sku.product)
        return None


class CartSerializer(serializers.ModelSerializer):
    """Serializer for cart structure expected by frontend."""

    items = serializers.SerializerMethodField()
    total_items = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = (
            "id",
            "user_id",
            "items",
            "total_items",
            "total_price",
        )

    def get_items(self, obj: Cart) -> List[Dict]:
        serializer = CartItemSerializer(
            obj.items.select_related("sku", "sku__product").prefetch_related(
                "sku__product__images"
            ),
            many=True,
            context=self.context,
        )
        return serializer.data

    def get_total_items(self, obj: Cart) -> int:
        return obj.total_items

    def get_total_price(self, obj: Cart) -> float:
        return float(obj.total_price or 0)


class WishlistItemSerializer(ProductSerializerMixin, serializers.ModelSerializer):
    """Serializer for wishlist items including product payload."""

    product = serializers.SerializerMethodField()

    class Meta:
        model = WishlistItem
        fields = (
            "id",
            "product",
            "created_at",
        )

    def get_product(self, obj: WishlistItem) -> Dict:
        return self._product_summary(obj.product)


class WishlistSerializer(serializers.ModelSerializer):
    """Serializer for wishlist response."""

    items = serializers.SerializerMethodField()

    class Meta:
        model = Wishlist
        fields = (
            "id",
            "user_id",
            "items",
        )

    def get_items(self, obj: Wishlist) -> List[Dict]:
        serializer = WishlistItemSerializer(
            obj.items.select_related("product")
            .prefetch_related("product__images", "product__skus"),
            many=True,
            context=self.context,
        )
        return serializer.data


class WishlistClearResponseSerializer(WishlistSerializer):
    """Serializer for wishlist payload returned after a clear operation."""

    success = serializers.BooleanField()
    message = serializers.CharField()

    class Meta(WishlistSerializer.Meta):
        fields = ("success", "message") + WishlistSerializer.Meta.fields


class StatelessUserRequestSerializer(serializers.Serializer):
    """Base request serializer for stateless cart & wishlist endpoints."""

    user_id = serializers.IntegerField(min_value=1)


class CartGetRequestSerializer(StatelessUserRequestSerializer):
    """Request body for retrieving a user's cart."""

    pass


class CartAddRequestSerializer(StatelessUserRequestSerializer):
    """Request body for adding an item to the cart."""

    sku_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, required=False, default=1)


class CartUpdateRequestSerializer(StatelessUserRequestSerializer):
    """Request body for updating a cart item's quantity."""

    cart_item_id = serializers.IntegerField()
    quantity = serializers.IntegerField()


class CartRemoveRequestSerializer(StatelessUserRequestSerializer):
    """Request body for removing an item from the cart."""

    cart_item_id = serializers.IntegerField()


class CartClearRequestSerializer(StatelessUserRequestSerializer):
    """Request body for clearing a cart."""

    pass


class WishlistGetRequestSerializer(StatelessUserRequestSerializer):
    """Request body for retrieving a wishlist."""

    pass


class WishlistAddRequestSerializer(StatelessUserRequestSerializer):
    """Request body for adding a product to the wishlist."""

    product_id = serializers.IntegerField()


class WishlistRemoveRequestSerializer(StatelessUserRequestSerializer):
    """Request body for removing a product from the wishlist."""

    product_id = serializers.IntegerField()


class WishlistClearRequestSerializer(StatelessUserRequestSerializer):
    """Request body for clearing a wishlist."""

    pass


class MarketCurrencySerializer(serializers.Serializer):
    """Serializer describing currency metadata for a market."""

    symbol = serializers.CharField()
    code = serializers.CharField()
    country = serializers.CharField()
    language = serializers.CharField()


class AvailableBrandSerializer(serializers.Serializer):
    """Serializer for a single available brand entry."""

    name = serializers.CharField()
    slug = serializers.CharField(allow_null=True)


class PriceRangeSerializer(serializers.Serializer):
    """Serializer representing minimum and maximum price."""

    min = serializers.FloatField()
    max = serializers.FloatField()


class ProductFiltersSerializer(serializers.Serializer):
    """Serializer for market-aware attribute filters."""

    available_sizes = serializers.ListField(
        child=serializers.CharField(), allow_empty=True
    )
    available_colors = serializers.ListField(
        child=serializers.CharField(), allow_empty=True
    )
    available_brands = AvailableBrandSerializer(many=True)
    price_range = PriceRangeSerializer()


class CategoryListResponseSerializer(serializers.Serializer):
    """Serializer for category collection responses."""

    categories = CategoryListSerializer(many=True, read_only=True)
    total = serializers.IntegerField()


class CategoryDetailResponseSerializer(serializers.Serializer):
    """Serializer for a category with nested subcategories."""

    category = CategoryDetailSerializer(read_only=True)
    subcategories = SubcategoryListSerializer(many=True, read_only=True)


class SubcategoryProductsResponseSerializer(serializers.Serializer):
    """Serializer for subcategory product listings with filters."""

    category = CategoryDetailSerializer(read_only=True)
    subcategory = SubcategoryListSerializer(read_only=True)
    products = ProductListSerializer(many=True, read_only=True)
    filters = ProductFiltersSerializer(read_only=True)
    total = serializers.IntegerField()
    page = serializers.IntegerField()
    limit = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    has_more = serializers.BooleanField()
    currency = MarketCurrencySerializer(read_only=True)


class ProductSearchResponseSerializer(serializers.Serializer):
    """Serializer for search endpoint responses."""

    products = ProductListSerializer(many=True, read_only=True)
    total = serializers.IntegerField()
    page = serializers.IntegerField()
    limit = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    has_more = serializers.BooleanField()
    currency = MarketCurrencySerializer(read_only=True)


