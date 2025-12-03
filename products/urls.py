"""
URL patterns for the products app.
"""

from django.urls import path, re_path

from .views import (
    CategoryDetailView,
    CategoryListView,
    PopularCategoriesView,
    CategorySubcategoryListView,
    CartAddView,
    CartClearView,
    CartGetView,
    CartRemoveView,
    CartUpdateView,
    ProductBestSellerView,
    ProductDetailView,
    ProductListView,
    ProductSearchView,
    ProductImageUploadView,
    SubcategoryProductsView,
    WishlistAddView,
    WishlistClearView,
    WishlistGetView,
    WishlistRemoveView,
)
from .views_currency import CurrencyListView, CurrencyConvertView, MarketCurrencyView, CurrencyUpdateRatesView

urlpatterns = [
    # Category endpoints
    re_path(r"^categories/?$", CategoryListView.as_view(), name="category-list"),
    re_path(r"^categories/popular/?$", PopularCategoriesView.as_view(), name="category-popular"),
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

    # Image upload endpoint
    re_path(r"^upload/image/?$", ProductImageUploadView.as_view(), name="product-image-upload"),

    # Cart endpoints (stateless)
    re_path(r"^cart/get/?$", CartGetView.as_view(), name="cart-get"),
    re_path(r"^cart/add/?$", CartAddView.as_view(), name="cart-add"),
    re_path(r"^cart/update/?$", CartUpdateView.as_view(), name="cart-update"),
    re_path(r"^cart/remove/?$", CartRemoveView.as_view(), name="cart-remove"),
    re_path(r"^cart/clear/?$", CartClearView.as_view(), name="cart-clear"),

    # Wishlist endpoints (stateless)
    re_path(r"^wishlist/get/?$", WishlistGetView.as_view(), name="wishlist-get"),
    re_path(r"^wishlist/add/?$", WishlistAddView.as_view(), name="wishlist-add"),
    re_path(r"^wishlist/remove/?$", WishlistRemoveView.as_view(), name="wishlist-remove"),
    re_path(r"^wishlist/clear/?$", WishlistClearView.as_view(), name="wishlist-clear"),

    # Legacy subcategory endpoint without category slug
    re_path(
        r"^subcategories/(?P<subcategory_slug>[-\w]+)/products/?$",
        SubcategoryProductsView.as_view(),
        name="subcategory-products",
    ),

    # Currency endpoints
    re_path(r"^currencies/?$", CurrencyListView.as_view(), name="currency-list"),
    re_path(r"^currencies/convert/?$", CurrencyConvertView.as_view(), name="currency-convert"),
    re_path(r"^currencies/market/?$", MarketCurrencyView.as_view(), name="market-currency"),
    re_path(r"^currencies/update-rates/?$", CurrencyUpdateRatesView.as_view(), name="currency-update-rates"),
]


