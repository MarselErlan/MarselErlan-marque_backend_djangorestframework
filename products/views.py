"""
Product API views.

These endpoints power the product catalogue for the Next.js storefront.
"""

from typing import Optional, Tuple

from django.db.models import Count, Max, Min, Prefetch, Q
from django.utils.text import slugify
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Review
from .models import Category, Product, Subcategory
from .serializers import (
    CategoryDetailSerializer,
    CategoryListSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    SubcategoryListSerializer,
)
from .utils import filter_by_market, get_market_currency, get_user_market_from_phone


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
            market = getattr(request.user, "market", None)
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
        return (
            Product.objects.filter(is_active=True)
            .select_related("category", "subcategory")
            .prefetch_related(
                "images",
                "skus",
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
                skus__size__in=[
                    size.strip() for size in sizes.split(",") if size.strip()
                ]
            )
        if colors := request.query_params.get("colors"):
            queryset = queryset.filter(
                skus__color__in=[
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
            base_queryset.values_list("skus__size", flat=True)
            .distinct()
            .exclude(skus__size__isnull=True)
        )
        colors = (
            base_queryset.values_list("skus__color", flat=True)
            .distinct()
            .exclude(skus__color__isnull=True)
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
    """

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(is_best_seller=True).order_by("-sales_count", "-rating")

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
            queryset = queryset.filter(skus__size__in=[size.strip() for size in sizes.split(",") if size.strip()])

        if colors := request.query_params.get("colors"):
            queryset = queryset.filter(skus__color__in=[color.strip() for color in colors.split(",") if color.strip()])

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

