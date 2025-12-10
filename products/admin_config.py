"""
Admin configuration for Products app.
This registers store owner admin classes that filter by user's stores.
"""

from django.contrib import admin
from .models import Product, SKU, ProductImage, ProductFeature
from .admin_store_owner import (
    StoreOwnerProductAdmin,
    StoreOwnerSKUAdmin,
    StoreOwnerProductImageAdmin,
    StoreOwnerProductFeatureAdmin,
)

# Unregister default admin if it exists
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

# Register store owner admin classes
# These automatically filter products by user's stores
admin.site.register(Product, StoreOwnerProductAdmin)
admin.site.register(SKU, StoreOwnerSKUAdmin)
admin.site.register(ProductImage, StoreOwnerProductImageAdmin)
admin.site.register(ProductFeature, StoreOwnerProductFeatureAdmin)

