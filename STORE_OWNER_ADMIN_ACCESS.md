# Store Owner Django Admin Access

## Overview

Store owners can access Django admin to manage their stores and products. Staff access is automatically granted when they register a store.

## How It Works

### 1. Store Registration (Automatic Staff Access)

When a user registers a store through the API (`/api/v1/stores/register/`):

- The store is created with status `pending`
- The authenticated user becomes the store owner
- **The owner is automatically granted `is_staff=True`** to access Django admin

**Location:** `stores/serializers.py` - `StoreRegistrationSerializer.create()`

### 2. Store Approval (Additional Staff Access Grant)

When a superuser approves a store in Django admin:

- Store status changes from `pending` to `active`
- Store `is_active` is set to `True`
- **The owner is granted `is_staff=True`** (if not already granted)

**Location:** `stores/admin_store_owner.py` - `approve_stores()` action and `save_model()` method

### 3. Accessing Django Admin

Store owners can access Django admin by:

1. **Go to:** `https://your-domain.com/admin/`
2. **Login with:** Their regular user credentials (phone number + password/OTP)
3. **They will see:**
   - **PRODUCTS** module - to manage their store's products (full CRUD)
   - **STORES** module - to view and update their store details (read-only for certain fields)

### 4. Admin Permissions

Store owners have **limited admin access**:

#### Products Admin:

- ✅ Can create, read, update, and delete products from their own stores
- ✅ Can only see products from stores they own
- ✅ Cannot change product store ownership
- ❌ Cannot see products from other stores

#### Stores Admin:

- ✅ Can view and update their own store details
- ✅ Can update: name, description, email, phone, website, address, logo, cover image
- ❌ Cannot add new stores
- ❌ Cannot delete stores
- ❌ Cannot change: owner, slug, market, status, is_active, is_verified, is_featured, contract dates

### 5. Admin URL

Store owners access admin at:

```
https://your-domain.com/admin/
```

They use their regular user credentials (same as the main website login).

## Security Notes

- Store owners only see data from their own stores
- All admin views are filtered by store ownership
- Superusers can see and manage everything
- Staff access is automatically granted - no manual setup needed

## Troubleshooting

### Store owner cannot access admin:

1. **Check if user has `is_staff=True`:**

   ```python
   # In Django shell
   from users.models import User
   user = User.objects.get(phone='+996555111111')
   print(user.is_staff)  # Should be True
   ```

2. **If `is_staff=False`, grant it manually:**

   ```python
   user.is_staff = True
   user.save()
   ```

3. **Or re-approve the store** (this will automatically grant staff access)

### Store owner sees "You don't have permission":

- This happens if the user has no active stores
- The admin modules are hidden if `user.owned_stores.filter(is_active=True).exists()` returns False
- Solution: Ensure the store is approved and active

## Code References

- **Store Registration:** `stores/serializers.py` - `StoreRegistrationSerializer`
- **Admin Configuration:** `stores/admin_store_owner.py` - `StoreOwnerStoreAdmin`
- **Product Admin:** `products/admin_store_owner.py` - `StoreOwnerProductAdmin`
- **Permissions:** `stores/permissions.py` - `IsStoreOwner`
