"""
URL configuration for banners app.
"""

from django.urls import re_path

from .views import (
    BannerListView,
    CategoryBannerListView,
    HeroBannerListView,
    PromoBannerListView,
)

urlpatterns = [
    re_path(r"^banners/?$", BannerListView.as_view(), name="banner-list"),
    re_path(r"^banners/hero/?$", HeroBannerListView.as_view(), name="banner-hero"),
    re_path(r"^banners/promo/?$", PromoBannerListView.as_view(), name="banner-promo"),
    re_path(
        r"^banners/category/?$",
        CategoryBannerListView.as_view(),
        name="banner-category",
    ),
]

