# Multi-Store Marketplace Implementation

## Overview

Transformed the single-store e-commerce platform into a multi-store marketplace (similar to Amazon, Wildberries). Business owners can now register stores and sell their products/services through the platform.

## What Was Implemented

### 1. New `stores` App

Created a new Django app for managing multiple stores on the platform.

**Models:**

- **Store**: Main store model with:
  - Basic info (name, slug, description)
  - Owner (business owner who manages the store)
  - Visual identity (logo, cover image)
  - Contact information (email, phone, website, address)
  - Statistics (rating, reviews_count, orders_count, products_count, likes_count)
  - Status management (pending, active, suspended, closed)
  - Market support (KG, US, ALL)
  - Contract tracking (signed_date, expiry_date)
- **StoreFollower**: Users can follow/subscribe to stores
  - Tracks user-store relationships
  - Automatically updates store likes_count

### 2. Product-Store Integration

- Added `store` ForeignKey to `Product` model
- Products can now belong to a specific store
- Updated product serializers to include store information
- Store info appears in product listings and detail pages

### 3. API Endpoints

#### Store Endpoints (`/api/v1/stores/`)

- `GET /api/v1/stores/` - List all active stores
  - Filters: `market` (KG/US), `limit`, `offset`
  - Returns: Store list with ratings, stats, and follow status
- `GET /api/v1/stores/{store_slug}/` - Get store details
  - Returns: Full store information including contact details
- `GET /api/v1/stores/{store_slug}/products/` - Get products from a store
  - Filters: `market`, `limit`, `offset`
  - Returns: List of products from that store
- `POST /api/v1/stores/{store_slug}/follow/` - Follow/Unfollow a store
  - Requires: Authentication
  - Toggles follow status
- `GET /api/v1/stores/{store_slug}/statistics/` - Get store statistics (owner only)
  - Requires: Authentication + Store ownership
  - Returns: Detailed statistics for store dashboard

### 4. Product Serializer Updates

- `ProductListSerializer` now includes `store` field with:
  - Store ID, name, slug
  - Store logo URL
  - Store rating and reviews count
  - Store verification status
- Store information automatically included in:
  - Product listings
  - Product detail pages
  - Search results
  - Category/subcategory product lists

### 5. Database Migrations

- `stores/migrations/0001_initial.py` - Creates Store and StoreFollower models
- `products/migrations/0012_*.py` - Adds store ForeignKey to Product model

## Usage Examples

### Creating a Store (via Admin or API)

```python
from stores.models import Store
from users.models import User

owner = User.objects.get(phone='+996555123456')
store = Store.objects.create(
    name='Azraud Store',
    owner=owner,
    market='KG',
    description='Premium clothing store',
    status='active',
    is_active=True
)
```

### Linking Products to Store

```python
from products.models import Product

product = Product.objects.get(slug='marque-tshirt')
product.store = store
product.save()
```

### API Usage

**List Stores:**

```bash
GET /api/v1/stores/?market=KG&limit=20
```

**Get Store Details:**

```bash
GET /api/v1/stores/azraud-store/
```

**Get Store Products:**

```bash
GET /api/v1/stores/azraud-store/products/?market=KG
```

**Follow Store:**

```bash
POST /api/v1/stores/azraud-store/follow/
Authorization: Token <user_token>
```

## Features

✅ Multi-store support  
✅ Store profiles with ratings and statistics  
✅ Product-store linking  
✅ Store following/subscription  
✅ Market-aware filtering (KG/US)  
✅ Store owner dashboard (statistics endpoint)  
✅ Store verification badges  
✅ Featured stores  
✅ Store logos and cover images

## Next Steps (Optional Enhancements)

1. **Store Registration API**: Allow business owners to register stores via API
2. **Store Management Dashboard**: Full CRUD operations for store owners
3. **Store Analytics**: More detailed analytics for store owners
4. **Store Reviews**: Allow users to review stores (not just products)
5. **Store Categories**: Categorize stores (Fashion, Electronics, etc.)
6. **Store Search**: Search stores by name, category, etc.
7. **Store Recommendations**: AI-powered store recommendations
8. **Commission System**: Track commissions per store
9. **Store Performance Metrics**: Sales trends, popular products, etc.

## Database Schema

```
stores_store
├── id (PK)
├── name
├── slug (unique)
├── owner (FK -> users_user)
├── market (KG/US/ALL)
├── logo, logo_url
├── cover_image, cover_image_url
├── rating, reviews_count, orders_count, products_count, likes_count
├── status (pending/active/suspended/closed)
├── is_active, is_verified, is_featured
└── timestamps

store_followers
├── id (PK)
├── user (FK -> users_user)
├── store (FK -> stores_store)
└── created_at

products_product
└── store (FK -> stores_store) [NEW]
```

## Testing

To test the implementation:

1. **Run migrations:**

   ```bash
   python manage.py migrate
   ```

2. **Create a test store** (via Django admin or shell)

3. **Link products to store**

4. **Test API endpoints:**
   - List stores
   - Get store details
   - Get store products
   - Follow/unfollow store

## Notes

- Existing products will have `store=None` (backward compatible)
- Store statistics are cached and can be updated via `store.update_statistics()`
- Store following automatically updates `likes_count`
- All store endpoints support market filtering (KG/US)
- Store information is included in all product responses
