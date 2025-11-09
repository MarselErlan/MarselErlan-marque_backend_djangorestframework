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
    Category,
    Product,
    ProductFeature,
    ProductImage,
    SKU,
    Subcategory,
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


class ProductImageSerializer(serializers.ModelSerializer):
    """Additional images for a product."""

    url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ("id", "url", "alt_text", "sort_order")

    @staticmethod
    def get_url(obj: ProductImage) -> str:
        return obj.image_url


class SKUSerializer(serializers.ModelSerializer):
    """Serializer for product variants (Size/Color combinations)."""

    price = serializers.SerializerMethodField()
    original_price = serializers.SerializerMethodField()

    class Meta:
        model = SKU
        fields = (
            "id",
            "sku_code",
            "size",
            "color",
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
    image = serializers.CharField()
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
        serializer = SKUSerializer(self._active_skus(obj), many=True)
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


