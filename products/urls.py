"""
URL patterns for the products app.
"""

from django.urls import path, re_path

from .views import (
    CategoryDetailView,
    CategoryListView,
    CategorySubcategoryListView,
    ProductBestSellerView,
    ProductDetailView,
    ProductListView,
    ProductSearchView,
    SubcategoryProductsView,
)

urlpatterns = [
    # Category endpoints
    re_path(r"^categories/?$", CategoryListView.as_view(), name="category-list"),
    re_path(r"^categories/(?P<slug>[-\w]+)/?$", CategoryDetailView.as_view(), name="category-detail"),
    re_path(
        r"^categories/(?P<slug>[-\w]+)/subcategories/?$",
        CategorySubcategoryListView.as_view(),
        name="category-subcategory-list",
    ),
    re_path(
        r"^categories/(?P<category_slug>[-\w]+)/subcategories/(?P<subcategory_slug>[-\w]+)/products/?$",
        SubcategoryProductsView.as_view(),
        name="category-subcategory-products",
    ),

    # List & search endpoints
    re_path(r"^products/?$", ProductListView.as_view(), name="product-list"),
    re_path(r"^products/best-sellers/?$", ProductBestSellerView.as_view(), name="product-best-sellers"),
    re_path(r"^products/search/?$", ProductSearchView.as_view(), name="product-search"),

    # Detail endpoint (slug or numeric ID)
    path("products/<str:identifier>", ProductDetailView.as_view(), name="product-detail"),
    path("products/<str:identifier>/", ProductDetailView.as_view(), name="product-detail-slash"),

    # Legacy subcategory endpoint without category slug
    re_path(
        r"^subcategories/(?P<subcategory_slug>[-\w]+)/products/?$",
        SubcategoryProductsView.as_view(),
        name="subcategory-products",
    ),
]


