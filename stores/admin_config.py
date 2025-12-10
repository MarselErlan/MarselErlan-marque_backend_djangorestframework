"""
Admin configuration for Stores app.
This registers store owner admin classes that filter by user's stores.
"""

from django.contrib import admin
from .models import Store
from .admin_store_owner import StoreOwnerStoreAdmin

# Unregister default admin if it exists
try:
    admin.site.unregister(Store)
except admin.sites.NotRegistered:
    pass

# Register store owner admin class
# This automatically filters stores by owner
admin.site.register(Store, StoreOwnerStoreAdmin)

