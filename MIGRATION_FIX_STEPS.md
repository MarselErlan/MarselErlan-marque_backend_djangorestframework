# Migration Fix Steps

## Current Problem

The migration failed because Django tried to directly convert `CharField` (strings) to `ForeignKey` (integers). We need to rollback and use the fixed migration.

## Steps to Fix

### 1. Rollback the Failed Migration

```bash
cd /Users/macbookpro/M4_Projects/Prodaction/marque_backend_with_drangorestframework
python manage.py migrate products 0006
```

This rolls back to the state before the failed migration.

### 2. The Fixed Migration File

I've already created a fixed migration file at:
`products/migrations/0007_brand_alter_product_brand.py`

This migration properly handles the data conversion by:

- Creating Brand model first
- Adding temporary `brand_fk` field
- Migrating data from old `brand` CharField to Brand objects
- Removing old field
- Renaming to final field name

### 3. Run the Fixed Migration

```bash
python manage.py migrate products
```

### 4. Verify

After migration succeeds:

- Check that brands table exists
- Check that products have brand ForeignKey linked
- Test API endpoints

## If Migration Still Fails

If you get errors, check:

1. **Database state**: Make sure you rolled back properly
2. **Brand table**: If it was partially created, you might need to drop it:
   ```sql
   DROP TABLE IF EXISTS products_brands CASCADE;
   ```
3. **Product table**: Check if `brand_fk` column exists (it shouldn't if you rolled back)

## Alternative: Manual Fix via SQL

If the migration continues to fail, you can run this manually:

```sql
-- 1. Create brands table (if not exists)
-- (Let Django create this via migration)

-- 2. Add brand_fk column
ALTER TABLE products_products ADD COLUMN brand_fk_id INTEGER NULL;
ALTER TABLE products_products ADD CONSTRAINT products_brand_fk_fkey
    FOREIGN KEY (brand_fk_id) REFERENCES products_brands(id);

-- 3. Create Brand objects and link products
-- (Use Django shell or the migration script)
```

But try the rollback + fixed migration first!
