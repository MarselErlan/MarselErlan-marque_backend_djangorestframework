# Single Database Architecture with Market Filtering

## 🎯 Important Concept

**There is ONE PostgreSQL database for the entire platform.**

The `market` column is used to **filter** which data to show, not to separate databases.

---

## 🗄️ Database Architecture

```
┌─────────────────────────────────────────────┐
│     ONE PostgreSQL Database (Railway)       │
│                                             │
│  ┌─────────────────────────────────────┐  │
│  │  Products Table                      │  │
│  │  ┌──────┬─────────┬────────┬─────┐  │  │
│  │  │  id  │  name   │ market │ ... │  │  │
│  │  ├──────┼─────────┼────────┼─────┤  │  │
│  │  │  1   │ T-Shirt │   KG   │ ... │  │  │
│  │  │  2   │ Jeans   │   US   │ ... │  │  │
│  │  │  3   │ Jacket  │   ALL  │ ... │  │  │
│  │  └──────┴─────────┴────────┴─────┘  │  │
│  └─────────────────────────────────────┘  │
│                                             │
│  ┌─────────────────────────────────────┐  │
│  │  Users Table                         │  │
│  │  ┌──────┬───────────┬────────┬────┐ │  │
│  │  │  id  │   phone   │ market │... │ │  │
│  │  ├──────┼───────────┼────────┼────┤ │  │
│  │  │  1   │ +996...   │   KG   │... │ │  │
│  │  │  2   │ +1...     │   US   │... │ │  │
│  │  └──────┴───────────┴────────┴────┘ │  │
│  └─────────────────────────────────────┘  │
│                                             │
│  ┌─────────────────────────────────────┐  │
│  │  Orders Table                        │  │
│  │  ┌──────┬─────────┬──────────┬────┐ │  │
│  │  │  id  │ user_id │  total   │... │ │  │
│  │  ├──────┼─────────┼──────────┼────┤ │  │
│  │  │  1   │    1    │ 1250 KGS │... │ │  │
│  │  │  2   │    2    │  $50 USD │... │ │  │
│  │  └──────┴─────────┴──────────┴────┘ │  │
│  │  (market inherited from user.market) │  │
│  └─────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

---

## 📊 How Market Filtering Works

### Customer Side

When a KG user logs in:

```sql
-- User's market is determined from phone
User: phone='+996505...', market='KG'

-- Products shown (filtered by market)
SELECT * FROM products
WHERE (market = 'KG' OR market = 'ALL')
  AND is_active = TRUE;

-- Categories shown
SELECT * FROM categories
WHERE (market = 'KG' OR market = 'ALL')
  AND is_active = TRUE;

-- Banners shown
SELECT * FROM banners
WHERE (market = 'KG' OR market = 'ALL')
  AND is_active = TRUE;
```

### Manager Side

When a manager switches to US market view:

```sql
-- Manager settings updated
UPDATE manager_settings
SET active_market = 'US'
WHERE manager_id = 1;

-- Orders shown (filtered by user's market)
SELECT * FROM orders
WHERE user_id IN (
    SELECT id FROM users WHERE market = 'US'
);

-- Revenue calculated (from US market orders)
SELECT SUM(total_amount)
FROM orders
WHERE user_id IN (
    SELECT id FROM users WHERE market = 'US'
)
AND order_date = CURRENT_DATE;
```

---

## 🔄 Market Switcher Behavior

### Frontend UI Shows:

- "KG DB" - **NOT a separate database**, just showing KG-filtered data
- "US DB" - **NOT a separate database**, just showing US-filtered data

### What Actually Happens:

1. Manager clicks market switcher
2. Frontend updates `active_market` state
3. All API requests include market parameter
4. Backend filters queries by market
5. Returns only data for selected market

**Example:**

```typescript
// Frontend
const [currentMarket, setCurrentMarket] = useState<"kg" | "us">("kg");

// When switching
const handleMarketChange = (newMarket: Market) => {
  setCurrentMarket(newMarket);
  localStorage.setItem("admin_market", newMarket);

  // Reload data with new filter
  fetchOrders({ market: newMarket });
  fetchRevenue({ market: newMarket });
};
```

```python
# Backend API
def get_orders(request):
    market = request.query_params.get('market', 'KG')

    # Filter orders by users from this market
    orders = Order.objects.filter(
        user__market=market
    )

    return Response(orders)
```

---

## 🎨 Models with Market Column

### Direct Market Field

These models have a `market` column for **direct filtering** (better performance):

| Model                | Market Column | Purpose                                      |
| -------------------- | ------------- | -------------------------------------------- |
| **User**             | `market`      | User's market (from phone)                   |
| **VerificationCode** | `market` ✨   | SMS provider routing (KG vs US providers)    |
| **Address**          | `market` ✨   | Address format & delivery service (auto-set) |
| **PaymentMethod**    | `market` ✨   | Payment gateway selection (auto-set)         |
| **Notification**     | `market` ✨   | Localized messaging (auto-set)               |
| **Product**          | `market`      | Product availability (KG/US/ALL)             |
| **Category**         | `market`      | Category availability (KG/US/ALL)            |
| **Banner**           | `market`      | Banner visibility (KG/US/ALL)                |
| **Order**            | `market`      | Order market (copied from user.market)       |
| **RevenueSnapshot**  | `market`      | Revenue tracking per market                  |

### Inherited Market (via Relations)

These models inherit market through relationships:

| Model            | Market Source          | How                     |
| ---------------- | ---------------------- | ----------------------- |
| **CartItem**     | `cart.user.market`     | Through Cart → User     |
| **WishlistItem** | `wishlist.user.market` | Through Wishlist → User |

---

## 🔍 Filtering Examples

### Get KG Products

```python
from products.models import Product
from products.utils import filter_by_market

# Get all active products for KG market
products = Product.objects.filter(is_active=True, in_stock=True)
kg_products = filter_by_market(products, 'KG')

# SQL: WHERE (market='KG' OR market='ALL') AND is_active=TRUE
```

### Get US Orders

```python
from orders.models import Order

# Get all orders from US market (direct field - faster!)
us_orders = Order.objects.filter(market='US')

# Or get today's US orders
from datetime import date
today_us_orders = Order.objects.filter(
    market='US',
    order_date__date=date.today()
)

# OLD WAY (still works but slower - requires JOIN):
# us_orders = Order.objects.filter(user__market='US')
```

### Why Order Has Direct Market Field

**Performance Optimization:**

```python
# ❌ OLD: Requires JOIN with users table (slower)
orders = Order.objects.filter(user__market='KG')

# ✅ NEW: Direct field lookup (faster)
orders = Order.objects.filter(market='KG')

# The market field is auto-populated from user.market on creation:
order = Order.objects.create(
    user=user,  # user.market = 'KG'
    # market='KG' is automatically set
    ...
)
```

**Benefits:**

- ⚡ **Faster queries** - No JOIN needed
- 📊 **Better indexes** - Direct index on market column
- 🎯 **Simpler queries** - Just `filter(market='KG')`
- 📈 **Manager dashboard** - Much faster filtering

### Calculate KG Revenue

```python
from store_manager.utils import calculate_revenue_snapshot

# Calculate today's KG revenue
kg_metrics = calculate_revenue_snapshot(market='KG')

# Returns metrics from orders where user.market='KG'
# {
#   'total_revenue': 7150.00,
#   'total_orders': 5,
#   'average_order_value': 1430.00,
#   ...
# }
```

---

## 🚀 Manager Permissions

Managers can be granted access to one or both markets:

```python
# Manager with access to KG market only
manager = StoreManager.objects.create(
    user=user,
    role='manager',
    can_manage_kg=True,   # ✅ Can see KG data
    can_manage_us=False,  # ❌ Cannot see US data
)

# Multi-market manager
admin = StoreManager.objects.create(
    user=admin_user,
    role='admin',
    can_manage_kg=True,   # ✅ Can see KG data
    can_manage_us=True,   # ✅ Can see US data
)

# Check accessible markets
manager.accessible_markets  # Returns: ['KG']
admin.accessible_markets    # Returns: ['KG', 'US']
```

---

## 📱 API Implementation Pattern

### Recommended API Pattern:

```python
# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from products.models import Product
from products.utils import filter_by_market

class ProductListView(APIView):
    def get(self, request):
        # Get user's market or default to KG
        if request.user.is_authenticated:
            user_market = request.user.market
        else:
            # Guest users - detect from header or default
            user_market = 'KG'

        # Get products filtered by market
        products = Product.objects.filter(
            is_active=True,
            in_stock=True
        )
        products = filter_by_market(products, user_market)

        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)
```

### Manager API Pattern:

```python
# manager/views.py
class ManagerOrdersView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        # Get manager's active market from settings
        manager = request.user.manager_profile
        active_market = manager.settings.active_market

        # Verify manager has permission for this market
        if active_market == 'KG' and not manager.can_manage_kg:
            return Response({'error': 'No access to KG market'}, status=403)
        if active_market == 'US' and not manager.can_manage_us:
            return Response({'error': 'No access to US market'}, status=403)

        # Get orders filtered by market
        orders = Order.objects.filter(
            user__market=active_market
        )

        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
```

---

## 💡 Key Takeaways

1. ✅ **ONE Database** - All data is in a single PostgreSQL database
2. ✅ **Market Column** - Used for filtering, not database separation
3. ✅ **User.market** - Automatically set from phone country code
4. ✅ **Product.market** - Manually set (KG/US/ALL)
5. ✅ **Manager Switching** - Changes filter, not database connection
6. ✅ **Revenue Analytics** - Calculated separately per market from same DB
7. ✅ **Permissions** - Managers can access one or both markets

---

## ⚠️ Common Misconceptions

### ❌ WRONG Thinking:

- "KG has its own database, US has its own database"
- "Market switching connects to different databases"
- "KG orders are stored separately from US orders"

### ✅ CORRECT Thinking:

- "ONE database with market filtering"
- "Market switching changes the WHERE clause in queries"
- "All orders are in the same table, filtered by user.market"

---

## 🎯 Benefits of This Architecture

### Advantages:

✅ **Simpler** - One database to manage
✅ **Cost-effective** - One database connection
✅ **Easier migrations** - Apply once to one DB
✅ **Better analytics** - Can compare markets easily
✅ **Flexible** - Easy to add new markets (just add to choices)
✅ **Consistent** - One source of truth

### Trade-offs:

⚠️ **Careful filtering required** - Must always filter by market
⚠️ **Index optimization** - Need indexes on market fields
⚠️ **Query awareness** - Developers must remember to filter

---

## 📋 Checklist for Developers

When implementing features:

- [ ] Does the model need a `market` field?
- [ ] Are queries filtered by market?
- [ ] Do managers have permission to access this market?
- [ ] Are analytics calculated per market?
- [ ] Is the active market tracked in logs?
- [ ] Are tests written for both markets?

---

**Remember: ONE Database, Multiple Markets, Filtered by Column!** 🎯
