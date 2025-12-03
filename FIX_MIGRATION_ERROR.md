# Fix Migration Error - Brand Field Conversion

## Problem

The migration failed because Django tried to directly convert a `CharField` (containing strings like "adidas") to a `ForeignKey` (which expects integer IDs). This doesn't work without a data migration.

## Solution Steps

### Step 1: Rollback the Failed Migration

First, you need to rollback the failed migration:

```bash
cd /Users/macbookpro/M4_Projects/Prodaction/marque_backend_with_drangorestframework
python manage.py migrate products 0006
```

This will rollback to migration `0006_currency_product_currency_sku_currency`.

### Step 2: Delete the Failed Migration File

```bash
rm products/migrations/0007_brand_alter_product_brand.py
```

### Step 3: Create a New Migration Manually

I've already created the fixed migration file. It should be at:
`products/migrations/0007_brand_alter_product_brand.py`

If it's not there or you want to verify it's correct, check the file.

### Step 4: Run the Migration Again

```bash
python manage.py migrate products
```

## What the Fixed Migration Does

The fixed migration follows this sequence:

1. **Creates Brand table** - New table for brands
2. **Adds temporary `brand_fk` field** - New nullable ForeignKey field
3. **Migrates data** - Extracts unique brand names, creates Brand objects, links products
4. **Removes old `brand` CharField** - Deletes the old string field
5. **Renames `brand_fk` to `brand`** - Final field name
6. **Updates related_name** - Sets correct relationship name

## Alternative: Manual Data Migration

If the migration still fails, you can manually migrate the data:

```python
# Run this in Django shell: python manage.py shell

from products.models import Product
from django.utils.text import slugify
from django.db import transaction

# First, you need to temporarily add Brand model to your models.py
# Then run this:

# Get unique brands
unique_brands = Product.objects.values_list('brand', flat=True).distinct()
unique_brands = {b.strip() for b in unique_brands if b and b.strip()}

print(f"Found {len(unique_brands)} unique brands")

# Create Brand instances (you'll need to import Brand model)
# This is just for reference - the migration should handle it
```

## If Migration Still Fails

If you continue to have issues:

1. **Check database state**: Make sure you've rolled back properly
2. **Check for partial changes**: The Brand table might have been created - you may need to drop it manually
3. **Use SQL directly**: You might need to run SQL commands directly in your database

Let me know if you need help with any of these steps!
