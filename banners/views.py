"""
Banner API views.
"""

from typing import Dict, Optional

from django.utils import timezone
from django.db.models import Q
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Banner
from .serializers import BannerSerializer


class BannerBaseView(APIView):
    """Common helpers for banner endpoints."""

    permission_classes = [AllowAny]
    default_market = "KG"

    def resolve_market(self, request) -> str:
        # Priority: authenticated user → X-Market header → query param → default
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

        return self.default_market

    def base_queryset(self, request):
        """Return filtered queryset for active banners respecting market & schedule."""
        market = self.resolve_market(request)
        now = timezone.now()
        return (
            Banner.objects.filter(is_active=True)
            .filter(
                Q(start_date__lte=now) | Q(start_date__isnull=True),
                Q(end_date__gte=now) | Q(end_date__isnull=True),
            )
            .filter(Q(market=market) | Q(market="ALL"))
            .order_by("sort_order", "-created_at")
        )

    def serialize(self, queryset, request):
        return BannerSerializer(
            queryset,
            many=True,
            context={"request": request},
        ).data


class BannerListView(BannerBaseView):
    """
    GET /api/v1/banners
    Returns hero/promo/category banners grouped with totals.
    """

    def get(self, request):
        limit = request.query_params.get("limit")
        try:
            limit = int(limit) if limit is not None else None
        except (TypeError, ValueError):
            limit = None

        queryset = self.base_queryset(request)

        hero_qs = queryset.filter(banner_type="hero")
        promo_qs = queryset.filter(banner_type="promo")
        category_qs = queryset.filter(banner_type="category")

        if limit is not None and limit > 0:
            hero_qs = hero_qs[:limit]
            promo_qs = promo_qs[:limit]
            category_qs = category_qs[:limit]

        response_payload: Dict[str, Optional[object]] = {
            "hero_banners": self.serialize(hero_qs, request),
            "promo_banners": self.serialize(promo_qs, request),
            "category_banners": self.serialize(category_qs, request),
            "total": queryset.count(),
        }
        return Response(response_payload)


class BannerTypeListView(BannerBaseView):
    """
    GET /api/v1/banners/<type>
    """

    banner_type = None

    def get(self, request):
        if not self.banner_type:
            return Response(
                {"detail": "Banner type not specified."},
                status=400,
            )

        limit = request.query_params.get("limit")
        try:
            limit = int(limit) if limit is not None else None
        except (TypeError, ValueError):
            limit = None

        queryset = self.base_queryset(request).filter(banner_type=self.banner_type)
        if limit is not None and limit > 0:
            queryset = queryset[:limit]

        serializer = BannerSerializer(
            queryset,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)


class HeroBannerListView(BannerTypeListView):
    banner_type = "hero"


class PromoBannerListView(BannerTypeListView):
    banner_type = "promo"


class CategoryBannerListView(BannerTypeListView):
    banner_type = "category"
