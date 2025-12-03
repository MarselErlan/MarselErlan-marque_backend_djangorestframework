# How to Run the Brand Migration

## Current Status

The migration file has been fixed and is ready to run. The table name issue has been resolved.

## Steps to Run Migration

### Step 1: Rollback the Failed Migration

If the migration partially ran and failed, you need to rollback first:

```bash
cd /Users/macbookpro/M4_Projects/Prodaction/marque_backend_with_drangorestframework
python manage.py migrate products 0006
```

This will rollback to migration `0006` (before the brand migration).

### Step 2: Check Migration Status

Verify the current state:

```bash
python manage.py showmigrations products
```

You should see:

- ✅ `0006_currency_product_currency_sku_currency` (applied)
- ⏭️ `0007_brand_alter_product_brand` (not applied)

### Step 3: Run the Migration

```bash
python manage.py migrate products
```

### Step 4: Verify

After migration succeeds:

1. **Check brands table:**

   ```bash
   python manage.py dbshell
   # Then in SQL:
   SELECT COUNT(*) FROM brands;
   SELECT * FROM brands LIMIT 5;
   ```

2. **Check products:**

   ```sql
   SELECT p.id, p.name, b.name as brand_name
   FROM products p
   LEFT JOIN brands b ON p.brand_id = b.id
   LIMIT 5;
   ```

3. **Test Django admin:**
   - Go to admin panel
   - Check that Brand model appears
   - Check that Products show brand as dropdown

## What the Migration Does

1. ✅ Creates `brands` table
2. ✅ Adds `brand_fk` field to `products` table
3. ✅ Extracts unique brand names from old `brand` CharField
4. ✅ Creates Brand objects for each unique brand
5. ✅ Links products to Brand objects via `brand_fk`
6. ✅ Removes old `brand` CharField
7. ✅ Renames `brand_fk` to `brand`
8. ✅ Updates related_name

## If Migration Still Fails

### Error: "relation does not exist"

This means the table name is wrong. The fixed migration now uses:

- `Product._meta.db_table` to get the correct table name dynamically

### Error: "field does not exist"

Make sure you rolled back properly before running the migration again.

### Manual Fix

If you continue to have issues, you can run the data migration manually:

```python
# In Django shell: python manage.py shell

from products.models import Product, Brand
from django.utils.text import slugify

# Get unique brands
unique_brands = set()
for product in Product.objects.all():
    if hasattr(product, 'brand') and product.brand:
        if isinstance(product.brand, str):
            unique_brands.add(product.brand.strip())

print(f"Found {len(unique_brands)} unique brands")

# Create Brand objects
brand_mapping = {}
for brand_name in unique_brands:
    slug = slugify(brand_name)
    brand, created = Brand.objects.get_or_create(
        slug=slug,
        defaults={'name': brand_name, 'is_active': True}
    )
    brand_mapping[brand_name] = brand

# Link products
for product in Product.objects.all():
    if hasattr(product, 'brand') and isinstance(product.brand, str):
        brand_name = product.brand.strip()
        if brand_name in brand_mapping:
            product.brand_fk = brand_mapping[brand_name]
            product.save(update_fields=['brand_fk'])

print("✅ Migration complete!")
```

But try the automatic migration first! 🚀
