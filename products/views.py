"""
Product API views.

These endpoints power the product catalogue for the Next.js storefront.
"""

import os
from io import BytesIO
from typing import Optional, Tuple
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Count, Max, Min, Prefetch, Q
from django.utils.text import slugify
from PIL import Image, UnidentifiedImageError
from rest_framework import status
from rest_framework import serializers
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)

from orders.models import Review
from .models import (
    Cart,
    CartItem,
    Category,
    Product,
    SKU,
    Subcategory,
    Wishlist,
    WishlistItem,
)
from .serializers import (
    CategoryDetailSerializer,
    CategoryListSerializer,
    ImageUploadSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    SubcategoryListSerializer,
    CartSerializer,
    WishlistSerializer,
    CartGetRequestSerializer,
    CartAddRequestSerializer,
    CartUpdateRequestSerializer,
    CartRemoveRequestSerializer,
    CartClearRequestSerializer,
    WishlistGetRequestSerializer,
    WishlistAddRequestSerializer,
    WishlistRemoveRequestSerializer,
    WishlistClearRequestSerializer,
    WishlistClearResponseSerializer,
    CategoryListResponseSerializer,
    CategoryDetailResponseSerializer,
    SubcategoryProductsResponseSerializer,
    ProductSearchResponseSerializer,
)
from .utils import filter_by_market, get_market_currency, get_user_market_from_phone


MARKET_QUERY_PARAM = OpenApiParameter(
    name="market",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    description="Optional market code override (e.g., KG, US).",
)

PAGE_QUERY_PARAM = OpenApiParameter(
    name="page",
    type=OpenApiTypes.INT,
    location=OpenApiParameter.QUERY,
    description="Page number (1-indexed).",
)

LIMIT_QUERY_PARAM = OpenApiParameter(
    name="limit",
    type=OpenApiTypes.INT,
    location=OpenApiParameter.QUERY,
    description="Maximum number of items to return.",
)

CATEGORY_FILTER_PARAM = OpenApiParameter(
    name="category",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    description="Filter by category slug.",
)

SUBCATEGORY_FILTER_PARAM = OpenApiParameter(
    name="subcategory",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    description="Filter by subcategory slug.",
)

BRAND_FILTER_PARAM = OpenApiParameter(
    name="brand",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    description="Filter by brand name.",
)

GENDER_FILTER_PARAM = OpenApiParameter(
    name="gender",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    description="Filter by gender code (e.g., MEN, WOMEN).",
)

QUERY_PARAM = OpenApiParameter(
    name="query",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    description="Full-text search query.",
)

SIZES_PARAM = OpenApiParameter(
    name="sizes",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    description="Comma-separated list of size filters (e.g., S,M,L).",
)

COLORS_PARAM = OpenApiParameter(
    name="colors",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    description="Comma-separated list of color filters.",
)

BRANDS_PARAM = OpenApiParameter(
    name="brands",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    description="Comma-separated list of brand filters.",
)

PRICE_MIN_PARAM = OpenApiParameter(
    name="price_min",
    type=OpenApiTypes.NUMBER,
    location=OpenApiParameter.QUERY,
    description="Minimum variant price filter.",
)

PRICE_MAX_PARAM = OpenApiParameter(
    name="price_max",
    type=OpenApiTypes.NUMBER,
    location=OpenApiParameter.QUERY,
    description="Maximum variant price filter.",
)

PRODUCT_SORT_PARAM = OpenApiParameter(
    name="sort_by",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    enum=["price_asc", "price_desc", "rating", "rating_desc", "popular", "bestsellers", "newest"],
    description="Sort order for products.",
)

SEARCH_SORT_PARAM = OpenApiParameter(
    name="sort_by",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    enum=["price_asc", "price_desc", "rating_desc", "bestsellers", "newest"],
    description="Sort order for search results.",
)

class MarketAwareAPIView(APIView):
    """
    Common helpers for market-aware API endpoints.
    """

    permission_classes = [AllowAny]
    default_market = "KG"

    def resolve_market(self, request) -> str:
        """
        Resolve the market for the current request.

        Priority:
            1. Authenticated user market
            2. `X-Market` header
            3. `market` query parameter
            4. Phone query parameter (derive from country code)
            5. Default market ("KG")
        """
        if request.user and request.user.is_authenticated:
            market = getattr(request.user, "location", None)
            if market:
                return market

        header_market = request.headers.get("X-Market")
        if header_market:
            return header_market.upper()

        query_market = request.query_params.get("market")
        if query_market:
            return query_market.upper()

        phone = request.query_params.get("phone")
        if phone:
            return get_user_market_from_phone(phone)

        return self.default_market

    @staticmethod
    def resolve_limit(request, default: int = 20, maximum: int = 100) -> int:
        try:
            limit = int(request.query_params.get("limit", default))
        except (TypeError, ValueError):
            return default
        return max(1, min(limit, maximum))

    @staticmethod
    def resolve_pagination(request, default_limit: int = 20, maximum_limit: int = 100) -> Tuple[int, int]:
        try:
            page = int(request.query_params.get("page", 1))
        except (TypeError, ValueError):
            page = 1
        page = max(page, 1)
        limit = MarketAwareAPIView.resolve_limit(request, default_limit, maximum_limit)
        return page, limit

    def base_queryset(self):
        """
        Base queryset with common select/prefetch combinations.
        """
        sku_prefetch = Prefetch(
            "skus",
            queryset=SKU.objects.select_related("size_option", "color_option"),
        )
        return (
            Product.objects.filter(is_active=True)
            .select_related("category", "subcategory")
            .prefetch_related(
                "images",
                sku_prefetch,
                "features",
            )
        )

    def apply_market_filter(self, queryset, market: Optional[str]):
        if not market:
            return queryset
        return filter_by_market(queryset, market)


class CategoryListView(MarketAwareAPIView):
    """
    GET /api/v1/categories
    """

    def get_queryset(self, request):
        market = self.resolve_market(request)
        product_filter = (
            Q(products__is_active=True, products__in_stock=True)
            & (Q(products__market=market) | Q(products__market="ALL"))
        )

        queryset = (
            Category.objects.filter(is_active=True)
            .order_by("sort_order", "name")
            .annotate(
                product_count=Count("products", filter=product_filter, distinct=True)
            )
        )
        return self.apply_market_filter(queryset, market)

    @extend_schema(
        summary="Retrieve categories",
        tags=["categories"],
        parameters=[MARKET_QUERY_PARAM],
        responses={200: CategoryListResponseSerializer},
    )
    def get(self, request):
        queryset = self.get_queryset(request)
        serializer = CategoryListSerializer(
            queryset,
            many=True,
            context={"request": request},
        )
        return Response(
            {
                "categories": serializer.data,
                "total": queryset.count(),
            },
            status=status.HTTP_200_OK,
        )


class CategoryDetailView(MarketAwareAPIView):
    """
    GET /api/v1/categories/<slug>
    """

    def get_category(self, request, slug: str) -> Optional[Category]:
        queryset = CategoryListView().get_queryset(request)
        return queryset.filter(slug=slug).first()

    def get_subcategories(self, category: Category, market: str):
        product_filter = (
            Q(products__is_active=True, products__in_stock=True)
            & (Q(products__market=market) | Q(products__market="ALL"))
        )
        return (
            Subcategory.objects.filter(category=category, is_active=True)
            .order_by("sort_order", "name")
            .annotate(
                product_count=Count("products", filter=product_filter, distinct=True)
            )
        )

    @extend_schema(
        summary="Retrieve category detail",
        tags=["categories"],
        parameters=[MARKET_QUERY_PARAM],
        responses={
            200: CategoryDetailResponseSerializer,
            404: OpenApiResponse(description="Category not found."),
        },
    )
    def get(self, request, slug: str):
        category = self.get_category(request, slug)
        if not category:
            return Response(
                {"detail": "Category not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        market = self.resolve_market(request)
        subcategories = self.get_subcategories(category, market)

        return Response(
            {
                "category": CategoryDetailSerializer(
                    category, context={"request": request}
                ).data,
                "subcategories": SubcategoryListSerializer(
                    subcategories, many=True, context={"request": request}
                ).data,
            },
            status=status.HTTP_200_OK,
        )


class CategorySubcategoryListView(CategoryDetailView):
    """
    GET /api/v1/categories/<slug>/subcategories
    """

    @extend_schema(
        summary="List subcategories for a category",
        tags=["categories"],
        parameters=[MARKET_QUERY_PARAM],
        responses={
            200: CategoryDetailResponseSerializer,
            404: OpenApiResponse(description="Category not found."),
        },
    )
    def get(self, request, slug: str):
        category = self.get_category(request, slug)
        if not category:
            return Response(
                {"detail": "Category not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        market = self.resolve_market(request)
        subcategories = self.get_subcategories(category, market)

        return Response(
            {
                "category": CategoryDetailSerializer(
                    category, context={"request": request}
                ).data,
                "subcategories": SubcategoryListSerializer(
                    subcategories, many=True, context={"request": request}
                ).data,
            },
            status=status.HTTP_200_OK,
        )


class SubcategoryProductsView(MarketAwareAPIView):
    """
    GET /api/v1/categories/<category_slug>/subcategories/<subcategory_slug>/products
    GET /api/v1/subcategories/<subcategory_slug>/products
    """

    default_limit = 20

    def get_base_queryset(self, request, category_slug: Optional[str], sub_slug: str):
        market = self.resolve_market(request)

        category_qs = CategoryListView().get_queryset(request)
        if category_slug:
            category = category_qs.filter(slug=category_slug).first()
        else:
            category = category_qs.filter(subcategories__slug=sub_slug).first()

        if not category:
            return None, None, None

        product_filter = (
            Q(products__is_active=True, products__in_stock=True)
            & (Q(products__market=market) | Q(products__market="ALL"))
        )

        subcategory_qs = (
            Subcategory.objects.filter(category=category, slug=sub_slug, is_active=True)
            .annotate(
                product_count=Count("products", filter=product_filter, distinct=True)
            )
        )
        subcategory = subcategory_qs.first()
        if not subcategory:
            return category, None, None

        products_qs = (
            self.base_queryset()
            .filter(category=category, subcategory=subcategory, in_stock=True)
        )
        products_qs = self.apply_market_filter(products_qs, market)
        return category, subcategory, products_qs

    @staticmethod
    def _apply_attribute_filters(queryset, request):
        if sizes := request.query_params.get("sizes"):
            queryset = queryset.filter(
                skus__size_option__name__in=[
                    size.strip() for size in sizes.split(",") if size.strip()
                ]
            )
        if colors := request.query_params.get("colors"):
            queryset = queryset.filter(
                skus__color_option__name__in=[
                    color.strip() for color in colors.split(",") if color.strip()
                ]
            )
        if brands := request.query_params.get("brands"):
            queryset = queryset.filter(
                brand__in=[brand.strip() for brand in brands.split(",") if brand.strip()]
            )
        price_min = request.query_params.get("price_min")
        if price_min:
            try:
                queryset = queryset.filter(skus__price__gte=float(price_min))
            except ValueError:
                pass
        price_max = request.query_params.get("price_max")
        if price_max:
            try:
                queryset = queryset.filter(skus__price__lte=float(price_max))
            except ValueError:
                pass
        return queryset

    @staticmethod
    def _get_available_filters(base_queryset):
        sizes = (
            base_queryset.values_list("skus__size_option__name", flat=True)
            .distinct()
            .exclude(skus__size_option__name__isnull=True)
        )
        colors = (
            base_queryset.values_list("skus__color_option__name", flat=True)
            .distinct()
            .exclude(skus__color_option__name__isnull=True)
        )
        brands = (
            base_queryset.values_list("brand", flat=True)
            .distinct()
            .exclude(brand__isnull=True)
            .exclude(brand__exact="")
        )
        price_agg = base_queryset.aggregate(
            min_price=Min("skus__price"),
            max_price=Max("skus__price"),
        )
        return {
            "available_sizes": sorted({size for size in sizes if size}),
            "available_colors": sorted({color for color in colors if color}),
            "available_brands": [
                {
                    "name": brand,
                    "slug": slugify(brand) if brand else None,
                }
                for brand in sorted({brand for brand in brands if brand})
            ],
            "price_range": {
                "min": float(price_agg["min_price"]) if price_agg["min_price"] else 0.0,
                "max": float(price_agg["max_price"]) if price_agg["max_price"] else 0.0,
            },
        }

    @staticmethod
    def _apply_sorting(queryset, sort_by: str):
        if sort_by == "price_asc":
            return queryset.annotate(min_sku_price=Min("skus__price")).order_by(
                "min_sku_price", "price"
            )
        if sort_by == "price_desc":
            return queryset.annotate(min_sku_price=Min("skus__price")).order_by(
                "-min_sku_price", "-price"
            )
        if sort_by in {"rating", "rating_desc"}:
            return queryset.order_by("-rating", "-sales_count")
        if sort_by == "popular" or sort_by == "bestsellers":
            return queryset.order_by("-sales_count", "-rating")
        if sort_by == "newest":
            return queryset.order_by("-created_at")
        return queryset.order_by("-created_at")

    @extend_schema(
        summary="List products within a subcategory",
        tags=["products"],
        parameters=[
            MARKET_QUERY_PARAM,
            PAGE_QUERY_PARAM,
            LIMIT_QUERY_PARAM,
            PRODUCT_SORT_PARAM,
            SIZES_PARAM,
            COLORS_PARAM,
            BRANDS_PARAM,
            PRICE_MIN_PARAM,
            PRICE_MAX_PARAM,
        ],
        responses={
            200: SubcategoryProductsResponseSerializer,
            400: OpenApiResponse(description="Subcategory slug is required."),
            404: OpenApiResponse(description="Category or subcategory not found."),
        },
    )
    def get(
        self,
        request,
        category_slug: Optional[str] = None,
        subcategory_slug: Optional[str] = None,
    ):
        sub_slug = subcategory_slug or category_slug
        if not sub_slug:
            return Response(
                {"detail": "Subcategory slug is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        category_lookup = category_slug if category_slug and category_slug != sub_slug else None

        category, subcategory, base_queryset = self.get_base_queryset(
            request, category_lookup, sub_slug
        )
        if category is None:
            return Response(
                {"detail": "Category not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if subcategory is None or base_queryset is None:
            return Response(
                {"detail": "Subcategory not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        filters_payload = self._get_available_filters(base_queryset)

        queryset = self._apply_attribute_filters(base_queryset, request).distinct()
        sort_by = request.query_params.get("sort_by", "popular")
        queryset = self._apply_sorting(queryset, sort_by)

        page, limit = self.resolve_pagination(request, self.default_limit)
        offset = (page - 1) * limit
        total = queryset.count()
        products = queryset[offset : offset + limit]

        serializer = ProductListSerializer(
            products,
            many=True,
            context={"request": request},
        )

        total_pages = (total + limit - 1) // limit if limit else 1
        currency = get_market_currency(self.resolve_market(request))

        response_payload = {
            "category": CategoryDetailSerializer(
                category, context={"request": request}
            ).data,
            "subcategory": SubcategoryListSerializer(
                subcategory, context={"request": request}
            ).data,
            "products": serializer.data,
            "filters": filters_payload,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_more": page < total_pages,
            "currency": currency,
        }

        return Response(response_payload, status=status.HTTP_200_OK)


class ProductImageUploadView(APIView):
    """
    POST /api/v1/upload/image
    Accepts multipart image files and stores them under MEDIA_ROOT/uploads/products/.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    @extend_schema(
        summary="Upload a product image",
        tags=["media"],
        request=ImageUploadSerializer,
        responses={
            201: inline_serializer(
                name="ProductImageUploadResponse",
                fields={
                    "success": serializers.BooleanField(),
                    "url": serializers.CharField(),
                    "path": serializers.CharField(),
                    "filename": serializers.CharField(),
                    "original_filename": serializers.CharField(),
                    "content_type": serializers.CharField(),
                    "size": serializers.IntegerField(),
                    "width": serializers.IntegerField(),
                    "height": serializers.IntegerField(),
                },
            )
        },
    )
    def post(self, request):
        serializer = ImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        upload = serializer.validated_data["image"]
        folder = serializer.validated_data.get("folder") or "products"

        # Validate image using Pillow
        try:
            upload.seek(0)
            pil_image = Image.open(upload)
            pil_image.verify()
            upload.seek(0)
            pil_image = Image.open(upload)
        except (UnidentifiedImageError, OSError):
            return Response(
                {"detail": "Invalid or unsupported image file."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        original_format = (pil_image.format or "").upper()
        has_alpha = pil_image.mode in ("RGBA", "LA", "P")

        if has_alpha and pil_image.mode != "RGBA":
            pil_image = pil_image.convert("RGBA")
        elif not has_alpha and pil_image.mode not in ("RGB", "L"):
            pil_image = pil_image.convert("RGB")

        # Resize if image exceeds 2048px on any side
        max_side = 2048
        if max(pil_image.size) > max_side:
            pil_image.thumbnail((max_side, max_side), Image.LANCZOS)

        # Decide output format
        if has_alpha:
            target_format = "PNG"
            extension = ".png"
            content_type = "image/png"
        elif original_format in {"JPEG", "JPG"}:
            target_format = "JPEG"
            extension = ".jpg"
            content_type = "image/jpeg"
        else:
            target_format = "JPEG"
            extension = ".jpg"
            content_type = "image/jpeg"

        buffer = BytesIO()
        save_kwargs = {
            "format": target_format,
        }
        if target_format == "JPEG":
            save_kwargs.update({"quality": 85, "optimize": True})
        pil_image.save(buffer, **save_kwargs)
        buffer.seek(0)

        # Ensure folder path is safe
        safe_folder = slugify(folder) if folder else "products"
        unique_filename = f"{uuid4().hex}{extension}"
        relative_path = os.path.join("uploads", safe_folder, unique_filename)
        saved_path = default_storage.save(relative_path, ContentFile(buffer.getvalue()))
        file_url = request.build_absolute_uri(default_storage.url(saved_path))

        return Response(
            {
                "success": True,
                "url": file_url,
                "path": saved_path.replace("\\", "/"),
                "filename": os.path.basename(saved_path),
                "original_filename": upload.name,
                "content_type": content_type,
                "size": buffer.getbuffer().nbytes,
                "width": pil_image.width,
                "height": pil_image.height,
            },
            status=status.HTTP_201_CREATED,
        )


User = get_user_model()


class BaseUserLookupMixin:
    """Common helpers for stateless cart & wishlist endpoints."""

    permission_classes = [AllowAny]

    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except (User.DoesNotExist, ValueError, TypeError):
            return None

    def parse_user_id(self, request):
        user_id = request.data.get("user_id")
        if user_id is None:
            return None, Response(
                {"detail": "user_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return None, Response(
                {"detail": "user_id must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = self.get_user(user_id)
        if not user:
            return None, Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return user, None


class CartBaseView(BaseUserLookupMixin, APIView):
    """Base class for cart operations."""

    def get_cart(self, user):
        cart, _created = Cart.objects.get_or_create(user=user)
        return cart

    def serialize_cart(self, cart, request):
        serializer = CartSerializer(cart, context={"request": request})
        return serializer.data


class CartGetView(CartBaseView):
    """POST /cart/get"""

    @extend_schema(
        summary="Fetch current cart",
        tags=["cart"],
        request=CartGetRequestSerializer,
        responses={200: CartSerializer},
    )
    def post(self, request):
        user, error = self.parse_user_id(request)
        if error:
            return error
        cart = self.get_cart(user)
        return Response(self.serialize_cart(cart, request), status=status.HTTP_200_OK)


class CartAddView(CartBaseView):
    """POST /cart/add"""

    @extend_schema(
        summary="Add item to cart",
        tags=["cart"],
        request=CartAddRequestSerializer,
        responses={200: CartSerializer},
    )
    def post(self, request):
        user, error = self.parse_user_id(request)
        if error:
            return error

        sku_id = request.data.get("sku_id")
        quantity = request.data.get("quantity", 1)

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            quantity = 1
        quantity = max(quantity, 1)

        if not sku_id:
            return Response(
                {"detail": "sku_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sku = SKU.objects.filter(id=sku_id, is_active=True).select_related("product").first()
        if not sku:
            return Response(
                {"detail": "SKU not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        cart = self.get_cart(user)
        with transaction.atomic():
            cart_item, created = CartItem.objects.select_for_update().get_or_create(
                cart=cart,
                sku=sku,
                defaults={"quantity": 0},
            )
            cart_item.quantity = cart_item.quantity + quantity
            cart_item.save()

        return Response(self.serialize_cart(cart, request), status=status.HTTP_200_OK)


class CartUpdateView(CartBaseView):
    """POST /cart/update"""

    @extend_schema(
        summary="Update cart item quantity",
        tags=["cart"],
        request=CartUpdateRequestSerializer,
        responses={200: CartSerializer},
    )
    def post(self, request):
        user, error = self.parse_user_id(request)
        if error:
            return error

        cart_item_id = request.data.get("cart_item_id")
        quantity = request.data.get("quantity")

        if cart_item_id is None or quantity is None:
            return Response(
                {"detail": "cart_item_id and quantity are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            cart_item_id = int(cart_item_id)
            quantity = int(quantity)
        except (TypeError, ValueError):
            return Response(
                {"detail": "cart_item_id and quantity must be integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart = self.get_cart(user)
        try:
            cart_item = cart.items.select_for_update().get(id=cart_item_id)
        except CartItem.DoesNotExist:
            return Response(
                {"detail": "Cart item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        with transaction.atomic():
            if quantity <= 0:
                cart_item.delete()
            else:
                cart_item.quantity = quantity
                cart_item.save()

        return Response(self.serialize_cart(cart, request), status=status.HTTP_200_OK)


class CartRemoveView(CartBaseView):
    """POST /cart/remove"""

    @extend_schema(
        summary="Remove item from cart",
        tags=["cart"],
        request=CartRemoveRequestSerializer,
        responses={200: CartSerializer},
    )
    def post(self, request):
        user, error = self.parse_user_id(request)
        if error:
            return error

        cart_item_id = request.data.get("cart_item_id")
        if cart_item_id is None:
            return Response(
                {"detail": "cart_item_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            cart_item_id = int(cart_item_id)
        except (TypeError, ValueError):
            return Response(
                {"detail": "cart_item_id must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart = self.get_cart(user)
        cart.items.filter(id=cart_item_id).delete()
        return Response(self.serialize_cart(cart, request), status=status.HTTP_200_OK)


class CartClearView(CartBaseView):
    """POST /cart/clear"""

    @extend_schema(
        summary="Clear cart",
        tags=["cart"],
        request=CartClearRequestSerializer,
        responses={200: CartSerializer},
    )
    def post(self, request):
        user, error = self.parse_user_id(request)
        if error:
            return error
        cart = self.get_cart(user)
        cart.items.all().delete()
        return Response(self.serialize_cart(cart, request), status=status.HTTP_200_OK)


class WishlistBaseView(BaseUserLookupMixin, APIView):
    """Base functionality for wishlist operations."""

    def get_wishlist(self, user):
        wishlist, _created = Wishlist.objects.get_or_create(user=user)
        return wishlist

    def serialize_wishlist(self, wishlist, request):
        serializer = WishlistSerializer(wishlist, context={"request": request})
        return serializer.data


class WishlistGetView(WishlistBaseView):
    """POST /wishlist/get"""

    @extend_schema(
        summary="Fetch wishlist",
        tags=["wishlist"],
        request=WishlistGetRequestSerializer,
        responses={200: WishlistSerializer},
    )
    def post(self, request):
        user, error = self.parse_user_id(request)
        if error:
            return error
        wishlist = self.get_wishlist(user)
        return Response(self.serialize_wishlist(wishlist, request), status=status.HTTP_200_OK)


class WishlistAddView(WishlistBaseView):
    """POST /wishlist/add"""

    @extend_schema(
        summary="Add product to wishlist",
        tags=["wishlist"],
        request=WishlistAddRequestSerializer,
        responses={200: WishlistSerializer},
    )
    def post(self, request):
        user, error = self.parse_user_id(request)
        if error:
            return error

        product_id = request.data.get("product_id")
        if not product_id:
            return Response(
                {"detail": "product_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return Response(
                {"detail": "Product not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        wishlist = self.get_wishlist(user)
        WishlistItem.objects.get_or_create(wishlist=wishlist, product=product)

        return Response(self.serialize_wishlist(wishlist, request), status=status.HTTP_200_OK)


class WishlistRemoveView(WishlistBaseView):
    """POST /wishlist/remove"""

    @extend_schema(
        summary="Remove product from wishlist",
        tags=["wishlist"],
        request=WishlistRemoveRequestSerializer,
        responses={200: WishlistSerializer},
    )
    def post(self, request):
        user, error = self.parse_user_id(request)
        if error:
            return error

        product_id = request.data.get("product_id")
        if not product_id:
            return Response(
                {"detail": "product_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        wishlist = self.get_wishlist(user)
        wishlist.items.filter(product_id=product_id).delete()

        return Response(self.serialize_wishlist(wishlist, request), status=status.HTTP_200_OK)


class WishlistClearView(WishlistBaseView):
    """POST /wishlist/clear"""

    @extend_schema(
        summary="Clear wishlist",
        tags=["wishlist"],
        request=WishlistClearRequestSerializer,
        responses={200: WishlistClearResponseSerializer},
    )
    def post(self, request):
        user, error = self.parse_user_id(request)
        if error:
            return error

        wishlist = self.get_wishlist(user)
        wishlist.items.all().delete()

        return Response(
            {
                "success": True,
                "message": "Wishlist cleared.",
                **self.serialize_wishlist(wishlist, request),
            },
            status=status.HTTP_200_OK,
        )


class ProductListView(MarketAwareAPIView):
    """
    GET /api/v1/products
    """

    def get_queryset(self, request):
        queryset = self.base_queryset().filter(in_stock=True)
        market = self.resolve_market(request)
        queryset = self.apply_market_filter(queryset, market)

        category_slug = request.query_params.get("category")
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        subcategory_slug = request.query_params.get("subcategory")
        if subcategory_slug:
            queryset = queryset.filter(subcategory__slug=subcategory_slug)

        brand = request.query_params.get("brand")
        if brand:
            queryset = queryset.filter(brand__iexact=brand)

        gender = request.query_params.get("gender")
        if gender:
            queryset = queryset.filter(gender=gender.upper())

        queryset = queryset.order_by("-is_featured", "-sales_count", "-rating", "-created_at")
        return queryset.distinct()

    @extend_schema(
        summary="List products",
        tags=["products"],
        parameters=[
            MARKET_QUERY_PARAM,
            CATEGORY_FILTER_PARAM,
            SUBCATEGORY_FILTER_PARAM,
            BRAND_FILTER_PARAM,
            GENDER_FILTER_PARAM,
            LIMIT_QUERY_PARAM,
        ],
        responses={200: ProductListSerializer(many=True)},
    )
    def get(self, request):
        queryset = self.get_queryset(request)
        limit = self.resolve_limit(request, default=25)
        serializer = ProductListSerializer(
            queryset[:limit],
            many=True,
            context={"request": request},
        )

        response = Response(serializer.data, status=status.HTTP_200_OK)
        response["X-Total-Count"] = queryset.count()
        response["X-Currency-Code"] = get_market_currency(self.resolve_market(request)).get("code")
        return response


class ProductBestSellerView(ProductListView):
    """
    GET /api/v1/products/best-sellers
    Returns products sorted by actual sales (sold_count) from delivered orders.
    """

    def get_queryset(self, request):
        # Get base queryset - this already applies market filtering and returns products
        # We'll use the serializer's sold_count calculation instead of annotation
        # to avoid complex query issues
        queryset = super().get_queryset(request)
        
        # Order by sales_count (from model), rating, and created_at
        # The serializer will calculate actual sold_count dynamically
        queryset = queryset.order_by(
            '-sales_count',
            '-rating',
            '-created_at'
        )
        
        return queryset

    @extend_schema(
        summary="List best-seller products",
        tags=["products"],
        parameters=[MARKET_QUERY_PARAM, LIMIT_QUERY_PARAM],
        responses={200: ProductListSerializer(many=True)},
    )
    def get(self, request):
        queryset = self.get_queryset(request)
        limit = self.resolve_limit(request, default=12)
        serializer = ProductListSerializer(
            queryset[:limit],
            many=True,
            context={"request": request},
        )
        response = Response(serializer.data, status=status.HTTP_200_OK)
        response["X-Total-Count"] = queryset.count()
        response["X-Currency-Code"] = get_market_currency(self.resolve_market(request)).get("code")
        return response


class ProductSearchView(MarketAwareAPIView):
    """
    GET /api/v1/products/search
    """

    @extend_schema(
        summary="Search products",
        tags=["products"],
        parameters=[
            MARKET_QUERY_PARAM,
            QUERY_PARAM,
            CATEGORY_FILTER_PARAM,
            SUBCATEGORY_FILTER_PARAM,
            SIZES_PARAM,
            COLORS_PARAM,
            BRANDS_PARAM,
            PRICE_MIN_PARAM,
            PRICE_MAX_PARAM,
            PAGE_QUERY_PARAM,
            LIMIT_QUERY_PARAM,
            SEARCH_SORT_PARAM,
        ],
        responses={200: ProductSearchResponseSerializer},
    )
    def get(self, request):
        query = request.query_params.get("query", "").strip()
        market = self.resolve_market(request)
        page, limit = self.resolve_pagination(request, default_limit=20)
        offset = (page - 1) * limit

        queryset = self.base_queryset().filter(in_stock=True)
        queryset = self.apply_market_filter(queryset, market)

        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(brand__icontains=query)
                | Q(description__icontains=query)
                | Q(category__name__icontains=query)
                | Q(subcategory__name__icontains=query)
            )

        # Additional filters
        if category_slug := request.query_params.get("category"):
            queryset = queryset.filter(category__slug=category_slug)
        if subcategory_slug := request.query_params.get("subcategory"):
            queryset = queryset.filter(subcategory__slug=subcategory_slug)

        if sizes := request.query_params.get("sizes"):
            queryset = queryset.filter(skus__size_option__name__in=[size.strip() for size in sizes.split(",") if size.strip()])

        if colors := request.query_params.get("colors"):
            queryset = queryset.filter(skus__color_option__name__in=[color.strip() for color in colors.split(",") if color.strip()])

        if brands := request.query_params.get("brands"):
            queryset = queryset.filter(brand__in=[brand.strip() for brand in brands.split(",") if brand.strip()])

        price_min = request.query_params.get("price_min")
        price_max = request.query_params.get("price_max")
        if price_min:
            try:
                queryset = queryset.filter(skus__price__gte=float(price_min))
            except ValueError:
                pass
        if price_max:
            try:
                queryset = queryset.filter(skus__price__lte=float(price_max))
            except ValueError:
                pass

        queryset = queryset.annotate(
            min_sku_price=Min("skus__price"),
        ).distinct()

        sort_by = request.query_params.get("sort_by")
        if sort_by == "price_asc":
            queryset = queryset.order_by("min_sku_price", "price")
        elif sort_by == "price_desc":
            queryset = queryset.order_by("-min_sku_price", "-price")
        elif sort_by == "rating_desc":
            queryset = queryset.order_by("-rating", "-sales_count")
        elif sort_by == "bestsellers":
            queryset = queryset.order_by("-sales_count", "-rating")
        else:
            queryset = queryset.order_by("-created_at")

        total = queryset.count()
        products = queryset[offset : offset + limit]

        serializer = ProductListSerializer(
            products,
            many=True,
            context={"request": request},
        )

        total_pages = (total + limit - 1) // limit if limit else 1
        currency = get_market_currency(market)

        return Response(
            {
                "products": serializer.data,
                "total": total,
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
                "has_more": page < total_pages,
                "currency": currency,
            },
            status=status.HTTP_200_OK,
        )


class ProductDetailView(MarketAwareAPIView):
    """
    GET /api/v1/products/<slug_or_id>
    """

    def get_queryset(self, request):
        reviews_prefetch = Prefetch(
            "reviews",
            queryset=Review.objects.select_related("user").filter(is_approved=True),
        )
        queryset = self.base_queryset().prefetch_related(reviews_prefetch)
        market = self.resolve_market(request)
        return self.apply_market_filter(queryset, market)

    def get_object(self, request, identifier: str) -> Optional[Product]:
        queryset = self.get_queryset(request)
        product = queryset.filter(slug=identifier).first()
        if product:
            return product

        if identifier.isdigit():
            return queryset.filter(id=int(identifier)).first()
        return None

    @extend_schema(
        summary="Retrieve product detail",
        tags=["products"],
        parameters=[MARKET_QUERY_PARAM],
        responses={
            200: ProductDetailSerializer,
            404: OpenApiResponse(description="Product not found."),
        },
    )
    def get(self, request, identifier: str):
        product = self.get_object(request, identifier)
        if not product:
            return Response(
                {
                    "detail": "Product not found.",
                    "slug": identifier,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ProductDetailSerializer(
            product,
            context={"request": request},
        )
        response = Response(serializer.data, status=status.HTTP_200_OK)
        currency = get_market_currency(self.resolve_market(request))
        response["X-Currency-Code"] = currency.get("code")
        response["X-Currency-Symbol"] = currency.get("symbol")
        return response

