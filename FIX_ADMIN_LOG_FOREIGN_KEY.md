# Fix Django Admin Log Foreign Key Error

## Problem

When trying to save changes in Django admin (stores or products), you get this error:

```
IntegrityError: insert or update on table "django_admin_log" violates foreign key constraint
"django_admin_log_user_id_c564eba6_fk_auth_user_id"
DETAIL: Key (user_id)=(9) is not present in table "auth_user".
```

## Root Cause

The project uses a **custom User model** (`users.User` with table name `users`), but the `django_admin_log` table still has a foreign key constraint pointing to the default `auth_user` table instead of the custom `users` table.

This happens because:

1. Django's admin log was created before the custom User model was properly configured
2. The foreign key constraint `django_admin_log_user_id_c564eba6_fk_auth_user_id` points to `auth_user.id`
3. But your actual users are in the `users` table, not `auth_user`
4. When Django tries to log an admin action, it fails because the foreign key points to the wrong table

## Solution

A migration has been created to fix this issue:

**File:** `users/migrations/0008_fix_admin_log_user_fk.py`

This migration:

1. **Deletes orphaned log entries** - Removes any admin log entries that reference users that don't exist
2. **Drops the old foreign key** - Removes the constraint pointing to `auth_user`
3. **Creates a new foreign key** - Points to the correct `users` table

## How to Apply the Fix

### On Production (Railway)

1. **Via Railway Dashboard Shell:**

   ```bash
   # Connect to Railway Dashboard Shell
   # Then run:
   python manage.py migrate users
   ```

2. **Verify the fix:**

   ```sql
   -- Check the foreign key constraint
   SELECT
       tc.constraint_name,
       kcu.column_name,
       ccu.table_name AS foreign_table_name
   FROM information_schema.table_constraints AS tc
   JOIN information_schema.key_column_usage AS kcu
       ON tc.constraint_name = kcu.constraint_name
   JOIN information_schema.constraint_column_usage AS ccu
       ON ccu.constraint_name = tc.constraint_name
   WHERE tc.table_name = 'django_admin_log'
       AND tc.constraint_type = 'FOREIGN KEY'
       AND kcu.column_name = 'user_id';
   ```

   You should see: `django_admin_log_user_id_fk_users_id` pointing to `users` table (not `auth_user`)

### On Local Development

```bash
python manage.py migrate users
```

## What This Fixes

✅ Store owners can now save changes to their stores in Django admin  
✅ Store owners can now save changes to their products in Django admin  
✅ All admin actions will be properly logged  
✅ No more `IntegrityError` when saving in admin

## Important Notes

- **Orphaned log entries will be deleted** - Any admin log entries referencing non-existent users will be removed
- **This is safe** - The migration only affects the admin log table, not your actual data
- **One-time fix** - Once applied, this issue won't occur again

## Verification

After applying the migration, try:

1. Log in as a store owner
2. Edit a store or product
3. Save the changes
4. It should work without errors!
