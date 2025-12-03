# Simple Migration Guide

## Run These Commands

Copy and paste these commands one by one:

### 1. Rollback (if migration failed before)

```bash
cd /Users/macbookpro/M4_Projects/Prodaction/marque_backend_with_drangorestframework
python manage.py migrate products 0006
```

### 2. Run Migration

```bash
python manage.py migrate products
```

### 3. Verify

```bash
python manage.py showmigrations products
```

## Or Use the Script

I've created a script that does everything:

```bash
cd /Users/macbookpro/M4_Projects/Prodaction/marque_backend_with_drangorestframework
./run_brand_migration.sh
```

## Expected Result

You should see:

```
Running migrations:
  Applying products.0007_brand_alter_product_brand...
  Created brand: Adidas (slug: adidas)
  ...
  ✅ Migrated X brands and updated Y products
```

## Done! ✅

After migration:

- Brand model will be created
- All products will be linked to Brand objects
- API will return brand as object with image support

The migration file is ready and fixed! 🚀
