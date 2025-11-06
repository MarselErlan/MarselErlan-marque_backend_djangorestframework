# Market-Based Filtering System

## Overview

The MARQUE platform supports multiple markets (countries) with market-specific content. Users see products, categories, and banners relevant to their market.

## Supported Markets

- **KG (Kyrgyzstan)**: Phone numbers starting with `+996`
- **US (United States)**: Phone numbers starting with `+1`
- **ALL**: Special value for content available in all markets

## How It Works

### 1. User Market Assignment

When a user logs in with their phone number, their market is automatically determined:

```python
# In authentication view
from products.utils import get_user_market_from_phone

phone = "+996505123456"
market = get_user_market_from_phone(phone)  # Returns 'KG'

user.market = market
user.save()
```

**Phone to Market Mapping:**

- `+996` → `KG` (Kyrgyzstan)
- `+1` → `US` (United States)
- Others → `KG` (Default)

### 2. Content Filtering

All market-aware models have a `market` field:

| Model      | Market Field | Values            |
| ---------- | ------------ | ----------------- |
| `User`     | `market`     | `KG`, `US`        |
| `Product`  | `market`     | `KG`, `US`, `ALL` |
| `Category` | `market`     | `KG`, `US`, `ALL` |
| `Banner`   | `market`     | `KG`, `US`, `ALL` |

### 3. Filtering Logic

Content is filtered to show items that:

- Match the user's market, OR
- Are available in ALL markets

```python
from products.utils import filter_by_market

# Example: Get products for a user's market
products = Product.objects.filter(is_active=True, in_stock=True)
products = filter_by_market(products, user.market)

# This returns:
# - Products with market='KG' if user.market='KG'
# - Products with market='ALL' (available everywhere)
```

## Implementation Examples

### API View Example

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from products.models import Product
from products.utils import filter_by_market

class ProductListView(APIView):
    def get(self, request):
        # Get user's market
        user_market = request.user.market if request.user.is_authenticated else 'KG'

        # Get products
        products = Product.objects.filter(
            is_active=True,
            in_stock=True
        )

        # Filter by market
        products = filter_by_market(products, user_market)

        # Serialize and return
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)
```

### Category Filtering Example

```python
from products.models import Category
from products.utils import filter_by_market

# Get categories for user's market
categories = Category.objects.filter(is_active=True)
categories = filter_by_market(categories, request.user.market)
```

### Banner Filtering Example

```python
from banners.models import Banner
from products.utils import filter_by_market

# Get active banners for user's market
banners = Banner.objects.filter(
    is_active=True,
    banner_type='hero'
)
banners = filter_by_market(banners, request.user.market)
```

## Database Indexes

Optimized indexes for fast market-based queries:

```python
# Products
indexes = [
    models.Index(fields=['market', 'is_active', 'in_stock']),
]

# Categories
indexes = [
    models.Index(fields=['market', 'is_active']),
]

# Banners
indexes = [
    models.Index(fields=['market', 'banner_type', 'is_active']),
]
```

## Admin Panel

Admin users can easily filter and manage content by market:

- **Products**: Filter by market in list view
- **Categories**: Filter by market in list view
- **Banners**: Filter by market in list view

## Market-Specific Settings

Each market has specific settings:

| Setting          | KG (Kyrgyzstan) | US (United States) |
| ---------------- | --------------- | ------------------ |
| Currency Symbol  | сом             | $                  |
| Currency Code    | KGS             | USD                |
| Default Language | Russian (ru)    | English (en)       |
| Country          | Kyrgyzstan      | United States      |

```python
from products.utils import get_market_currency

# Get currency info for user's market
currency_info = get_market_currency(user.market)
# Returns: {'symbol': 'сом', 'code': 'KGS', 'country': 'Kyrgyzstan', 'language': 'ru'}
```

## Frontend Integration

### API Requests

The frontend should include the user's market in product requests:

```typescript
// Get products for current user's market
const products = await productsApi.getAll();
// Backend filters by user.market automatically

// Get categories for current user's market
const categories = await categoriesApi.getAll();
// Backend filters by user.market automatically
```

### Guest Users

For non-authenticated users:

- Default to `KG` market
- OR detect market from IP geolocation
- OR detect from browser language settings

```python
def get_guest_market(request):
    """Determine market for guest users"""
    # Option 1: Default
    return 'KG'

    # Option 2: From Accept-Language header
    language = request.headers.get('Accept-Language', '').lower()
    if 'en' in language:
        return 'US'
    return 'KG'
```

## Best Practices

### 1. Always Filter by Market

```python
# ✅ GOOD
products = Product.objects.filter(is_active=True)
products = filter_by_market(products, user.market)

# ❌ BAD - Shows all markets
products = Product.objects.filter(is_active=True)
```

### 2. Use 'ALL' for Universal Content

Products/categories/banners available everywhere should use `market='ALL'`:

```python
# Create a universal product
product = Product.objects.create(
    name="Universal T-Shirt",
    market='ALL',  # Available in all markets
    ...
)
```

### 3. Market-Specific Pricing

Consider adding market-specific pricing if needed:

```python
# Different prices for different markets
if user.market == 'US':
    price_usd = product.price  # Already in USD
elif user.market == 'KG':
    price_kgs = product.price  # Already in KGS
```

## Testing

### Test Market Filtering

```python
from django.test import TestCase
from products.models import Product
from products.utils import filter_by_market

class MarketFilteringTest(TestCase):
    def test_kg_user_sees_kg_and_all_products(self):
        # Create products
        kg_product = Product.objects.create(market='KG', ...)
        us_product = Product.objects.create(market='US', ...)
        all_product = Product.objects.create(market='ALL', ...)

        # Filter for KG user
        products = Product.objects.all()
        kg_filtered = filter_by_market(products, 'KG')

        # Should see KG and ALL products only
        self.assertIn(kg_product, kg_filtered)
        self.assertIn(all_product, kg_filtered)
        self.assertNotIn(us_product, kg_filtered)
```

## Migration Checklist

- [x] Added `market` field to `User` model
- [x] Added `market` field to `Product` model
- [x] Added `market` field to `Category` model
- [x] Added `market` field to `Banner` model
- [x] Created database indexes for market fields
- [x] Updated admin panels to show market field
- [x] Created utility functions for market filtering
- [ ] Implement market filtering in API views
- [ ] Add tests for market filtering
- [ ] Update frontend to handle market-specific content

## Future Enhancements

1. **Auto-detect market from IP**: Use geolocation services
2. **Market-specific pricing**: Different prices per market
3. **Market-specific shipping**: Different shipping costs
4. **Market-specific payment methods**: Region-specific payment options
5. **Multi-currency support**: Real-time currency conversion
6. **Market-specific promotions**: Region-specific discounts

---

**Questions?** Contact the development team for assistance with market filtering implementation.
