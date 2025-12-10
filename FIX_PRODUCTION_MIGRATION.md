# 🔧 Fix Production Database Migration Error

## Problem

You're seeing this error on production:

```
ProgrammingError: column store_managers.store_id does not exist
```

This happens because the migration `0003_storemanager_store.py` hasn't been run on your production database.

---

## ✅ Solution: Run Migrations on Production

### Step 1: Check Migration Status

On your production server (Railway), run:

```bash
python manage.py showmigrations store_manager
```

You should see:

```
store_manager
 [X] 0001_initial
 [X] 0002_initial
 [ ] 0003_storemanager_store  <-- This one is missing!
```

### Step 2: Run Missing Migration

Run the migration on production:

```bash
python manage.py migrate store_manager
```

Or run all pending migrations:

```bash
python manage.py migrate
```

### Step 3: Verify

After running migrations, check again:

```bash
python manage.py showmigrations store_manager
```

All should be marked with `[X]`:

```
store_manager
 [X] 0001_initial
 [X] 0002_initial
 [X] 0003_storemanager_store  <-- Now applied!
```

---

## 🚀 Quick Fix Commands

### For Railway (Production):

1. **SSH into your Railway instance** or use Railway CLI:

```bash
railway run python manage.py migrate store_manager
```

Or if using Railway dashboard:

- Go to your service
- Open "Shell" or "Deploy Logs"
- Run: `python manage.py migrate store_manager`

2. **Or run all migrations:**

```bash
railway run python manage.py migrate
```

---

## 📋 What This Migration Does

The migration `0003_storemanager_store.py` adds:

- A `store` ForeignKey field to `StoreManager` model
- Links managers to specific stores (for store-specific dashboards)
- Allows `null=True` for platform-wide managers

**This is safe to run** - it only adds a new nullable column.

---

## ⚠️ Important Notes

1. **Backup First**: Always backup your production database before running migrations
2. **Downtime**: This migration should be quick (just adding a column), minimal downtime
3. **Test Locally**: Make sure migrations work locally first

---

## 🔍 Verify Fix

After running migrations:

1. **Refresh Django Admin** - The error should be gone
2. **Check StoreManager Admin** - You should see the `store` field
3. **Test Store Admin** - Should work without errors

---

## 🆘 If Migration Fails

If you get errors during migration:

1. **Check database connection**
2. **Check if table exists**: `store_managers`
3. **Check if column already exists** (might have been partially applied)

To check manually (PostgreSQL):

```sql
-- Check if column exists
SELECT column_name
FROM information_schema.columns
WHERE table_name='store_managers' AND column_name='store_id';

-- If it doesn't exist, the migration needs to run
```

---

## ✅ After Fix

Once migrations are applied:

- ✅ Django Admin will work correctly
- ✅ StoreManager will have `store` field
- ✅ Store owners can manage their stores
- ✅ No more `ProgrammingError`

---

**Ready to fix?** Run the migration command on your production server!
