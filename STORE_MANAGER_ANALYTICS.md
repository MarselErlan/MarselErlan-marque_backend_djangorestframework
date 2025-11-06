# Store Manager Analytics - Enhanced Insights 📊

## Overview

Added 5 powerful analytics functions to `store_manager/utils.py` that leverage the new Order model references to Address and PaymentMethod for deeper business insights.

---

## New Analytics Functions

### 1. Payment Method Analytics

**Function:** `get_payment_method_analytics(market, date_from, date_to)`

Analyzes which payment methods customers prefer.

**Returns:**

- Payment type breakdown (card, cash, bank_transfer, digital_wallet)
- Card type breakdown (visa, mastercard, mir, amex)
- Revenue per payment method

**Example:**

```python
from store_manager.utils import get_payment_method_analytics
from datetime import date, timedelta

# Get last 30 days of KG payment data
analytics = get_payment_method_analytics(
    market='KG',
    date_from=date.today() - timedelta(days=30),
    date_to=date.today()
)

print(analytics)
```

**Output:**

```python
{
    'market': 'KG',
    'date_from': date(2025, 10, 7),
    'date_to': date(2025, 11, 6),
    'currency': 'сом',
    'total_orders': 450,
    'payment_types': [
        {'payment_method': 'cash', 'count': 250, 'revenue': Decimal('125000')},
        {'payment_method': 'card', 'count': 150, 'revenue': Decimal('95000')},
        {'payment_method': 'bank_transfer', 'count': 50, 'revenue': Decimal('30000')},
    ],
    'card_types': [
        {'card_type': 'mir', 'count': 80, 'revenue': Decimal('45000')},
        {'card_type': 'visa', 'count': 50, 'revenue': Decimal('35000')},
        {'card_type': 'mastercard', 'count': 20, 'revenue': Decimal('15000')},
    ]
}
```

**Business Insights:**

- Cash on Delivery is most popular (56%)
- MIR cards dominate in KG market
- Can optimize payment gateway costs

---

### 2. Delivery Location Analytics

**Function:** `get_delivery_location_analytics(market, date_from, date_to, top_n)`

Analyzes where orders are being delivered.

**Returns:**

- Top cities by order count
- Top cities by revenue
- State breakdown (US market only)

**Example:**

```python
from store_manager.utils import get_delivery_location_analytics

# Get top 10 cities for US market
analytics = get_delivery_location_analytics(
    market='US',
    top_n=10
)

print(analytics)
```

**Output:**

```python
{
    'market': 'US',
    'date_from': date(2025, 10, 7),
    'date_to': date(2025, 11, 6),
    'currency': '$',
    'total_orders': 320,
    'top_cities': [
        {'delivery_city': 'New York', 'count': 85, 'revenue': Decimal('4250.00')},
        {'delivery_city': 'Los Angeles', 'count': 65, 'revenue': Decimal('3450.00')},
        {'delivery_city': 'Chicago', 'count': 45, 'revenue': Decimal('2340.00')},
    ],
    'top_states': [
        {'delivery_state': 'NY', 'count': 90, 'revenue': Decimal('4500.00')},
        {'delivery_state': 'CA', 'count': 75, 'revenue': Decimal('3890.00')},
        {'delivery_state': 'IL', 'count': 50, 'revenue': Decimal('2560.00')},
    ]
}
```

**Business Insights:**

- Focus marketing on high-volume cities
- Optimize delivery routes
- Identify expansion opportunities

---

### 3. Popular Addresses

**Function:** `get_popular_addresses(market, top_n)`

Finds the most frequently used saved addresses.

**Uses:** The `shipping_address` ForeignKey on Order model

**Example:**

```python
from store_manager.utils import get_popular_addresses

# Get top 10 addresses for KG market
popular = get_popular_addresses(market='KG', top_n=10)

print(popular)
```

**Output:**

```python
{
    'market': 'KG',
    'currency': 'сом',
    'popular_addresses': [
        {
            'address_id': 123,
            'title': 'Home',
            'city': 'Bishkek',
            'full_address': 'г. Бишкек, микрорайон 6, дом 12, кв. 45',
            'order_count': 25,
            'total_revenue': Decimal('12500')
        },
        {
            'address_id': 456,
            'title': 'Office',
            'city': 'Bishkek',
            'full_address': 'г. Бишкек, ул. Чуй 265',
            'order_count': 18,
            'total_revenue': Decimal('9500')
        },
    ]
}
```

**Business Insights:**

- Identify loyal customers
- Optimize delivery partnerships for popular areas
- Target promotions to frequent buyers

---

### 4. Popular Payment Methods

**Function:** `get_popular_payment_methods(market, top_n)`

Finds the most frequently used saved payment methods.

**Uses:** The `payment_method_used` ForeignKey on Order model

**Example:**

```python
from store_manager.utils import get_popular_payment_methods

# Get top payment methods
popular = get_popular_payment_methods(market='US', top_n=10)

print(popular)
```

**Output:**

```python
{
    'market': 'US',
    'currency': '$',
    'popular_payment_methods': [
        {
            'payment_id': 789,
            'payment_type': 'card',
            'card_type': 'visa',
            'card_masked': '**** **** **** 1234',
            'order_count': 42,
            'total_revenue': Decimal('2150.00')
        },
        {
            'payment_id': 790,
            'payment_type': 'card',
            'card_type': 'amex',
            'card_masked': '**** ****** *5678',
            'order_count': 35,
            'total_revenue': Decimal('1890.00')
        },
    ]
}
```

**Business Insights:**

- Understand customer payment preferences
- Optimize payment gateway costs
- Identify high-value payment methods

---

### 5. Customer Analytics

**Function:** `get_customer_analytics(market, date_from, date_to)`

Analyzes customer behavior and loyalty.

**Returns:**

- Total customers
- Repeat customer rate
- Top customers by revenue
- Average orders per customer

**Example:**

```python
from store_manager.utils import get_customer_analytics

# Analyze KG customers for last month
analytics = get_customer_analytics(
    market='KG',
    date_from=date.today() - timedelta(days=30)
)

print(analytics)
```

**Output:**

```python
{
    'market': 'KG',
    'date_from': date(2025, 10, 7),
    'date_to': date(2025, 11, 6),
    'currency': 'сом',
    'total_customers': 285,
    'repeat_customers': 95,
    'repeat_rate': 33.33,  # 33.33% repeat rate
    'top_customers': [
        {
            'user_id': 101,
            'phone': '+996505123456',
            'name': 'Azamat Bekmurzaev',
            'order_count': 8,
            'total_spent': Decimal('15000')
        },
        {
            'user_id': 102,
            'phone': '+996555234567',
            'name': 'Asel Toktogulova',
            'order_count': 6,
            'total_spent': Decimal('12000')
        },
    ]
}
```

**Business Insights:**

- Track customer loyalty
- Identify VIP customers for special treatment
- Measure repeat purchase success
- Target retention campaigns

---

## Usage in Manager Dashboard

### Dashboard Statistics View

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from store_manager.utils import (
    get_payment_method_analytics,
    get_delivery_location_analytics,
    get_customer_analytics
)

class ManagerDashboardAnalyticsView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        # Get manager's active market
        manager = request.user.manager_profile
        market = manager.settings.active_market

        # Verify permission
        if market == 'KG' and not manager.can_manage_kg:
            return Response({'error': 'No access'}, status=403)

        # Get analytics
        analytics = {
            'payment_methods': get_payment_method_analytics(market=market),
            'delivery_locations': get_delivery_location_analytics(market=market, top_n=5),
            'customer_insights': get_customer_analytics(market=market),
        }

        return Response(analytics)
```

### Payment Analytics Endpoint

```python
class PaymentAnalyticsView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        market = request.query_params.get('market', 'KG')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        analytics = get_payment_method_analytics(
            market=market,
            date_from=date_from,
            date_to=date_to
        )

        return Response(analytics)
```

### Location Heatmap Endpoint

```python
class DeliveryHeatmapView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        market = request.query_params.get('market', 'KG')

        analytics = get_delivery_location_analytics(
            market=market,
            top_n=20  # Get top 20 locations
        )

        # Transform for heatmap visualization
        heatmap_data = [
            {
                'location': city['delivery_city'],
                'value': city['count'],
                'revenue': float(city['revenue'])
            }
            for city in analytics['top_cities']
        ]

        return Response({'heatmap': heatmap_data})
```

---

## Market-Specific Insights

### KG Market

```python
# KG-specific analytics
kg_analytics = {
    'payment_methods': get_payment_method_analytics(market='KG'),
    'popular_addresses': get_popular_addresses(market='KG'),
}

# Insights for KG:
# - Cash on Delivery dominates
# - MIR cards are most common
# - Bishkek has highest order volume
# - Building/Apartment addressing system
```

### US Market

```python
# US-specific analytics
us_analytics = {
    'payment_methods': get_payment_method_analytics(market='US'),
    'delivery_locations': get_delivery_location_analytics(market='US'),
}

# Insights for US:
# - Card payments dominate
# - Visa/Amex are most common
# - State-level breakdown available
# - Street addressing system
```

---

## Comparison Reports

### Payment Method Comparison

```python
def compare_payment_methods():
    """Compare payment preferences across markets"""

    kg_payments = get_payment_method_analytics(market='KG')
    us_payments = get_payment_method_analytics(market='US')

    return {
        'kg': kg_payments,
        'us': us_payments,
        'insights': {
            'kg_cash_preference': kg_payments['payment_types'][0]['payment_method'] == 'cash',
            'us_card_preference': us_payments['payment_types'][0]['payment_method'] == 'card',
        }
    }
```

### Customer Loyalty Comparison

```python
def compare_customer_loyalty():
    """Compare repeat rates across markets"""

    kg_customers = get_customer_analytics(market='KG')
    us_customers = get_customer_analytics(market='US')

    return {
        'kg_repeat_rate': kg_customers['repeat_rate'],
        'us_repeat_rate': us_customers['repeat_rate'],
        'better_market': 'KG' if kg_customers['repeat_rate'] > us_customers['repeat_rate'] else 'US'
    }
```

---

## Benefits

| Feature                   | Benefit                                  |
| ------------------------- | ---------------------------------------- |
| 📊 **Payment Analytics**  | Optimize payment gateway costs           |
| 🗺️ **Location Analytics** | Improve delivery routes and partnerships |
| 🏠 **Popular Addresses**  | Identify loyal customers                 |
| 💳 **Popular Payments**   | Understand customer payment preferences  |
| 👥 **Customer Insights**  | Improve retention and loyalty programs   |
| 🌍 **Market Comparison**  | Understand market differences            |
| 📈 **Data-Driven**        | Make informed business decisions         |

---

## Performance Notes

### Efficient Queries

All functions use Django ORM aggregation for optimal performance:

```python
# Direct aggregation (fast!)
orders.values('payment_method').annotate(
    count=Count('id'),
    revenue=Sum('total_amount')
)

# Uses indexes on market field
orders = Order.objects.filter(market=market)

# Leverages ForeignKey relationships
addresses = Address.objects.filter(
    orders_shipped_to__isnull=False
).annotate(
    order_count=Count('orders_shipped_to')
)
```

### Database Indexes

Existing indexes support these analytics:

```python
# Order indexes
models.Index(fields=['market', 'status'])
models.Index(fields=['market', '-created_at'])

# Address relationship
related_name='orders_shipped_to'

# PaymentMethod relationship
related_name='orders_paid_with'
```

---

## Summary

✅ **Added 5 powerful analytics functions**
✅ **Leverages Order references** to Address and PaymentMethod
✅ **Market-specific insights** for KG and US
✅ **Efficient queries** using Django ORM aggregation
✅ **Business intelligence** for data-driven decisions
✅ **Ready for API** endpoints and dashboard integration
✅ **No migration needed** - pure analytics layer

These analytics give managers deep insights into customer behavior, payment preferences, and delivery patterns! 📊

---

**Related Documentation:**

- [Order Snapshot Pattern](ORDER_SNAPSHOT_PATTERN.md)
- [User Market Fields](USER_MARKET_FIELDS.md)
- [Store Manager Guide](STORE_MANAGER_GUIDE.md)
