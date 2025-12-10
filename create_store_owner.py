#!/usr/bin/env python
"""
Quick script to create a test store owner account.
Run: python manage.py shell < create_store_owner.py
Or: python manage.py shell -c "$(cat create_store_owner.py)"
"""

from users.models import User
from stores.models import Store

# Create store owner user
store_owner = User.objects.create_user(
    phone='+996555999888',
    password='storeowner123',
    full_name='Test Store Owner',
    location='KG',
    is_staff=True,  # REQUIRED for admin access
    is_active=True,
    is_verified=True
)

# Create store for this user
store = Store.objects.create(
    name='Test Store Owner Store',
    slug='test-store-owner-store',
    owner=store_owner,
    market='KG',
    status='active',
    is_active=True,
    description='Test store for store owner admin access'
)

print("=" * 60)
print("✅ Store Owner Account Created!")
print("=" * 60)
print(f"Phone: {store_owner.phone}")
print(f"Password: storeowner123")
print(f"Store: {store.name}")
print(f"Store Status: {store.status}")
print("=" * 60)
print("\n📝 To login as store owner:")
print(f"   1. Logout from current session")
print(f"   2. Go to: /admin/")
print(f"   3. Username: {store_owner.phone}")
print(f"   4. Password: storeowner123")
print("\n✅ You'll see only this store and its products!")

