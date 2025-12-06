# Flexible Catalog System Implementation

## Overview

The catalog system now supports a flexible 3-level hierarchy:

- **Level 1**: Category → Products (direct)
- **Level 2**: Category → Subcategory → Products
- **Level 3**: Category → Subcategory → Subcategory → Products

Products can be assigned at any level, and the system automatically handles routing and queries based on the catalog structure.

## Database Changes

### Subcategory Model

- Added `parent_subcategory` field (self-referential ForeignKey) to support nested subcategories
- Updated `unique_together` constraints to handle both first-level and second-level subcategories
- Added `level` property to identify subcategory level (1 or 2)
- Added validation to ensure parent subcategory belongs to the same category

### Product Model

- Added `second_subcategory` field for 3-level catalog structure
- Updated indexes to support efficient querying across all catalog levels
- Added validation in `clean()` method to ensure catalog structure consistency:
  - If `second_subcategory` is set, `subcategory` must also be set
  - `second_subcategory` must be a child of `subcategory`
  - All subcategories must belong to the same category

## API Endpoints

### Level 1: Category Products

```
GET /api/v1/categories/{slug}/products
```

Returns products directly linked to the category (no subcategory).

### Level 2: Subcategory Products

```
GET /api/v1/categories/{category_slug}/subcategories/{subcategory_slug}/products
```

Returns products linked to the first-level subcategory (no second_subcategory).

### Level 3: Second-Level Subcategory Products

```
GET /api/v1/categories/{category_slug}/subcategories/{subcategory_slug}/subcategories/{second_subcategory_slug}/products
```

Returns products linked to the second-level subcategory.

## Usage Examples

### Creating a Level 1 Product

```python
product = Product.objects.create(
    name="Product Name",
    category=category,
    subcategory=None,  # No subcategory
    second_subcategory=None,  # No second subcategory
    price=100.00,
    # ... other fields
)
```

### Creating a Level 2 Product

```python
product = Product.objects.create(
    name="Product Name",
    category=category,
    subcategory=first_level_subcategory,  # First-level subcategory
    second_subcategory=None,  # No second subcategory
    price=100.00,
    # ... other fields
)
```

### Creating a Level 3 Product

```python
# First, create the subcategory hierarchy
first_subcategory = Subcategory.objects.create(
    category=category,
    name="First Level",
    parent_subcategory=None  # First-level has no parent
)

second_subcategory = Subcategory.objects.create(
    category=category,
    name="Second Level",
    parent_subcategory=first_subcategory  # Second-level has parent
)

# Then create the product
product = Product.objects.create(
    name="Product Name",
    category=category,
    subcategory=first_subcategory,
    second_subcategory=second_subcategory,
    price=100.00,
    # ... other fields
)
```

## Serializer Changes

### SubcategoryListSerializer

- Added `child_subcategories` field to show nested subcategories
- Added `level` field to indicate subcategory level
- Automatically includes child subcategories when serializing first-level subcategories

### Product Serializers

- Added `second_subcategory` field to all product serializers
- Maintains backward compatibility with existing API consumers

## View Changes

### CategoryDetailView

- Updated `get_subcategories()` to only return first-level subcategories
- Product count includes only level 2 products (products with subcategory but no second_subcategory)

### SubcategoryProductsView

- Updated to handle both 2-level and 3-level routing
- Automatically filters products based on catalog level:
  - Level 2: `subcategory=X, second_subcategory=None`
  - Level 3: `subcategory=X, second_subcategory=Y`

### CategoryProductsView (New)

- New view for level 1 products
- Returns products directly linked to category (no subcategory)

## Migration

Run the migration to apply database changes:

```bash
python manage.py migrate products
```

The migration file is: `0011_add_flexible_catalog_structure.py`

## Validation Rules

1. **Subcategory Validation**:

   - Parent subcategory must belong to the same category
   - First-level subcategories have `parent_subcategory=None`
   - Second-level subcategories must have a valid `parent_subcategory`

2. **Product Validation**:
   - If `second_subcategory` is set, `subcategory` must also be set
   - `second_subcategory` must be a child of `subcategory`
   - All subcategories must belong to the same category as the product

## Frontend Integration

The frontend can now:

1. Display nested subcategories in the catalog sidebar
2. Navigate through 1, 2, or 3 levels of catalog structure
3. Query products at any catalog level
4. Handle products that may be at different catalog levels within the same category

## Backward Compatibility

- Existing products with only `category` and `subcategory` continue to work (Level 2)
- Existing products with only `category` continue to work (Level 1)
- API responses include `second_subcategory` field (null for level 1 and 2 products)
- All existing endpoints remain functional

## Testing

When testing the new catalog system:

1. Create products at all three levels
2. Verify that products appear in the correct catalog level
3. Test API endpoints for all three levels
4. Verify that product counts are correct at each level
5. Test validation rules to ensure data integrity
