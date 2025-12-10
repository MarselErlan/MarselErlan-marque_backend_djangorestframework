"""
Django Admin Configuration for Store Owners.
This file configures the admin site to show store-specific admin interfaces.
"""

from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from products.admin_store_owner import (
    StoreOwnerProductAdmin,
    StoreOwnerSKUAdmin,
    StoreOwnerProductImageAdmin,
    StoreOwnerProductFeatureAdmin,
)
from stores.admin_store_owner import StoreOwnerStoreAdmin
from products.models import Product, SKU, ProductImage, ProductFeature
from stores.models import Store


# Unregister default admin if registered
try:
    admin.site.unregister(Product)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(SKU)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(ProductImage)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(ProductFeature)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(Store)
except admin.sites.NotRegistered:
    pass


# Register store owner admin classes
# These will automatically filter based on user permissions
admin.site.register(Product, StoreOwnerProductAdmin)
admin.site.register(SKU, StoreOwnerSKUAdmin)
admin.site.register(ProductImage, StoreOwnerProductImageAdmin)
admin.site.register(ProductFeature, StoreOwnerProductFeatureAdmin)
admin.site.register(Store, StoreOwnerStoreAdmin)


# Customize admin site header and title
admin.site.site_header = "Marque Marketplace Administration"
admin.site.site_title = "Marque Admin"
admin.site.index_title = "Store Management Dashboard"

