# Brand Model Migration Guide

## Overview

This document outlines the changes made to implement a proper Brand model with name, image, and relationship to products.

## Changes Made

### 1. Created Brand Model (`products/models.py`)

- Added `Brand` model with:
  - `name` (CharField, unique)
  - `slug` (SlugField, unique, auto-generated)
  - `image` (ImageField, optional)
  - `is_active` (BooleanField)
  - Timestamps (created_at, updated_at)

### 2. Updated Product Model

- Changed `brand = models.CharField(max_length=100)` to:
  ```python
  brand = models.ForeignKey(
      'Brand',
      on_delete=models.PROTECT,
      related_name='products',
      null=True,
      blank=True
  )
  ```
- Updated `__str__` method to use `brand.name` instead of direct brand string
- Updated slug generation to use `brand.slug` instead of brand string

### 3. Updated Serializers (`products/serializers.py`)

- Updated `_brand_payload()` to return brand object with:
  - `id`
  - `name`
  - `slug`
  - `image` (full URL)
- Updated `get_brand_name()` to use `obj.brand.name` instead of `obj.brand`
- Updated all brand references in serializers

### 4. Updated Admin (`products/admin.py`)

- Registered `BrandAdmin` with proper fieldsets
- Updated `ProductAdmin` search_fields to use `brand__name`

### 5. Next Steps - Update Views (`products/views.py`)

**IMPORTANT**: The following changes need to be made in `views.py`:

1. **Line 451-453** - Brand filtering:

   ```python
   # OLD:
   brand__in=[brand.strip() for brand in brands.split(",") if brand.strip()]

   # NEW:
   brand__slug__in=[brand.strip() for brand in brands.split(",") if brand.strip()]
   ```

2. **Line 481-486** - Get available brands:

   ```python
   # OLD:
   brands = base_queryset.values_list("brand", flat=True)

   # NEW:
   brands = base_queryset.values_list("brand__name", flat=True)
   ```

3. **Line 494-499** - Build brand filter response:

   ```python
   # OLD:
   "name": brand,
   "slug": slugify(brand) if brand else None,

   # NEW:
   "name": brand.name if brand else None,
   "slug": brand.slug if brand else None,
   ```

4. **Line 1138-1140** - Brand filter in ProductListView:

   ```python
   # OLD:
   queryset = queryset.filter(brand__iexact=brand)

   # NEW:
   queryset = queryset.filter(brand__slug__iexact=brand)
   ```

5. **Line 1255** - Brand search:

   ```python
   # OLD:
   Q(brand__icontains=query)

   # NEW:
   Q(brand__name__icontains=query)
   ```

6. **Line 1273-1274** - Brand filter in search:

   ```python
   # OLD:
   brand__in=[brand.strip() for brand in brands.split(",") if brand.strip()]

   # NEW:
   brand__slug__in=[brand.strip() for brand in brands.split(",") if brand.strip()]
   ```

## Migration Steps

1. Create migration:

   ```bash
   python manage.py makemigrations products
   ```

2. **IMPORTANT**: Before running migration, you need a data migration script to:

   - Create Brand instances from existing product.brand strings
   - Link products to the created Brand instances
   - This prevents data loss

3. Run migration:

   ```bash
   python manage.py migrate products
   ```

4. Update all views.py references as outlined above

5. Test thoroughly:
   - Product listing with brand filters
   - Product search by brand
   - Brand filtering in subcategory views
   - Admin interface for brands

## Notes

- The Brand model uses `PROTECT` on delete, so brands cannot be deleted if they have products
- Brand slugs are auto-generated from names
- Brand images are stored in `brands/` directory
- The serializer returns brand as an object with `id`, `name`, `slug`, and `image` for better frontend integration
