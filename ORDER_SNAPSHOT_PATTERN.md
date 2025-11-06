# Order Snapshot Pattern - Data Integrity 📸

## Overview

The `Order` model uses the **SNAPSHOT pattern** - a best practice in e-commerce that ensures order data remains intact even if users modify or delete their saved addresses and payment methods.

---

## The Problem

Without snapshots, if a user:

- Deletes their saved address
- Updates their payment method
- Changes their phone number

...the order would lose critical information or show incorrect data!

---

## The Solution: Dual Approach

### 1. Reference (ForeignKey) - For Tracking

Link to the Address and PaymentMethod for:

- User purchase history ("You ordered this to 123 Main St")
- Analytics (which addresses/payments are most used)
- Quick reorder (use same address/payment)

```python
shipping_address = models.ForeignKey(
    Address,
    on_delete=models.SET_NULL,  # Don't delete order if address is deleted
    null=True,
    blank=True,
    related_name='orders_shipped_to'
)

payment_method_used = models.ForeignKey(
    PaymentMethod,
    on_delete=models.SET_NULL,  # Don't delete order if payment is deleted
    null=True,
    blank=True,
    related_name='orders_paid_with'
)
```

### 2. Snapshot (Text Fields) - For Data Integrity

Copy the data at order time:

- Delivery address, city, state, postal code, country
- Payment method, card type, last 4 digits
- Customer name, phone, email

```python
# Delivery information (SNAPSHOT - preserved at order time)
delivery_address = models.TextField()
delivery_city = models.CharField(max_length=100, null=True, blank=True)
delivery_state = models.CharField(max_length=100, null=True, blank=True)
delivery_postal_code = models.CharField(max_length=20, null=True, blank=True)
delivery_country = models.CharField(max_length=100, default='Kyrgyzstan')
delivery_notes = models.TextField(null=True, blank=True)

# Payment (SNAPSHOT - preserved at order time)
payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
card_type = models.CharField(max_length=20, null=True, blank=True)
card_last_four = models.CharField(max_length=4, null=True, blank=True)
```

---

## How It Works

### Automatic Snapshotting

When an order is created, the `save()` method automatically copies data:

```python
def save(self, *args, **kwargs):
    if not self.pk and self.user:  # Only on creation
        # Copy market
        self.market = self.user.market

        # Copy country based on market
        if not self.delivery_country:
            self.delivery_country = 'Kyrgyzstan' if self.market == 'KG' else 'United States'

        # SNAPSHOT from shipping_address
        if self.shipping_address:
            self.delivery_address = self.shipping_address.full_address
            self.delivery_city = self.shipping_address.city
            self.delivery_state = self.shipping_address.state
            self.delivery_postal_code = self.shipping_address.postal_code
            self.delivery_country = self.shipping_address.country

        # SNAPSHOT from payment_method_used
        if self.payment_method_used:
            self.payment_method = self.payment_method_used.payment_type
            self.card_type = self.payment_method_used.card_type
            # Extract last 4 digits from "**** **** **** 1234"
            if self.payment_method_used.card_number_masked:
                self.card_last_four = self.payment_method_used.card_number_masked.replace('*', '').replace(' ', '')[-4:]

    super().save(*args, **kwargs)
```

---

## Usage Examples

### Creating an Order with References

```python
from orders.models import Order
from users.models import User, Address, PaymentMethod

# Get user's selected address and payment
user = User.objects.get(phone='+996505123456')
address = user.addresses.filter(is_default=True, market='KG').first()
payment = user.payment_methods.filter(is_default=True, market='KG').first()

# Create order with references
order = Order.objects.create(
    user=user,
    shipping_address=address,  # Reference
    payment_method_used=payment,  # Reference

    # Snapshot fields are AUTO-FILLED from address/payment
    # But you can also provide them manually:
    customer_name=user.get_full_name(),
    customer_phone=user.phone,
    customer_email=user.email,

    # Pricing
    subtotal=500.00,
    shipping_cost=100.00,
    tax=0.00,
    total_amount=600.00,
    currency='сом',
    currency_code='KGS',
)

# Snapshot fields are automatically populated!
print(order.delivery_address)  # Copied from address.full_address
print(order.delivery_city)  # Copied from address.city
print(order.card_type)  # Copied from payment.card_type
print(order.card_last_four)  # Extracted from payment.card_number_masked
```

### Creating Order Without References (Guest Checkout)

```python
# Guest checkout - no references, just snapshots
order = Order.objects.create(
    user=None,  # Guest
    market='KG',

    # No references
    shipping_address=None,
    payment_method_used=None,

    # Provide snapshot data manually
    customer_name="Guest User",
    customer_phone="+996555123456",
    customer_email="guest@example.com",

    delivery_address="г. Бишкек, ул. Ленина 123, кв. 45",
    delivery_city="Bishkek",
    delivery_country="Kyrgyzstan",

    payment_method='cash',
    payment_status='pending',

    total_amount=600.00,
    currency='сом',
    currency_code='KGS',
)
```

---

## Benefits of This Pattern

### ✅ Data Integrity

```python
# User creates order
order = Order.objects.create(
    user=user,
    shipping_address=user.addresses.first(),
    ...
)
print(order.delivery_address)  # "123 Main St, New York, NY 10001"

# User deletes their address
user.addresses.all().delete()

# Order data is PRESERVED!
order.refresh_from_db()
print(order.shipping_address)  # None (deleted)
print(order.delivery_address)  # Still "123 Main St, New York, NY 10001" ✅
```

### ✅ Purchase History

```python
# User can see where they ordered to
user_orders = Order.objects.filter(user=user)
for order in user_orders:
    if order.shipping_address:
        # Link still exists
        print(f"Ordered to: {order.shipping_address.title}")
    else:
        # Link deleted, but snapshot preserved
        print(f"Ordered to (deleted address): {order.delivery_address}")
```

### ✅ Analytics

```python
# Which addresses are most used?
popular_addresses = Address.objects.annotate(
    order_count=Count('orders_shipped_to')
).order_by('-order_count')

# Which payment methods are most used?
popular_payments = PaymentMethod.objects.annotate(
    order_count=Count('orders_paid_with')
).order_by('-order_count')
```

### ✅ Quick Reorder

```python
def reorder(previous_order):
    """Create new order with same address/payment"""
    return Order.objects.create(
        user=previous_order.user,
        shipping_address=previous_order.shipping_address,  # Reuse if not deleted
        payment_method_used=previous_order.payment_method_used,  # Reuse if not deleted
        # ... new order items ...
    )
```

---

## What Gets Snapshotted

### Delivery Information

| Snapshot Field         | Source                           | Market-Specific |
| ---------------------- | -------------------------------- | --------------- |
| `delivery_address`     | `address.full_address`           | ✅              |
| `delivery_city`        | `address.city`                   | ✅              |
| `delivery_state`       | `address.state`                  | ✅ (US only)    |
| `delivery_postal_code` | `address.postal_code`            | ✅              |
| `delivery_country`     | `address.country` or from market | ✅              |
| `delivery_notes`       | User input                       | No              |

### Payment Information

| Snapshot Field   | Source                              | Market-Specific |
| ---------------- | ----------------------------------- | --------------- |
| `payment_method` | `payment.payment_type`              | ✅              |
| `card_type`      | `payment.card_type`                 | ✅ (MIR = KG)   |
| `card_last_four` | Extracted from `card_number_masked` | No              |
| `payment_status` | Set by payment gateway              | No              |

### Customer Information

| Snapshot Field   | Source                 | Market-Specific |
| ---------------- | ---------------------- | --------------- |
| `customer_name`  | `user.get_full_name()` | No              |
| `customer_phone` | `user.phone`           | ✅              |
| `customer_email` | `user.email`           | No              |

---

## Market-Specific Examples

### KG Order

```python
order = Order.objects.create(
    user=kg_user,
    market='KG',
    shipping_address=kg_address,
    payment_method_used=kg_payment,

    # Auto-snapshotted:
    delivery_city='Bishkek',
    delivery_state=None,  # Not used in KG
    delivery_country='Kyrgyzstan',
    card_type='mir',  # MIR card (KG only)
    currency='сом',
    currency_code='KGS',
)
```

### US Order

```python
order = Order.objects.create(
    user=us_user,
    market='US',
    shipping_address=us_address,
    payment_method_used=us_payment,

    # Auto-snapshotted:
    delivery_city='New York',
    delivery_state='NY',  # Required for US
    delivery_postal_code='10001',  # ZIP code
    delivery_country='United States',
    card_type='amex',  # American Express (common in US)
    currency='$',
    currency_code='USD',
)
```

---

## Admin Panel Display

The Django admin clearly shows both references and snapshots:

```python
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    fieldsets = (
        ('References', {
            'fields': ('shipping_address', 'payment_method_used'),
            'description': 'Links to address/payment (for history)'
        }),
        ('Delivery Information (Snapshot)', {
            'fields': ('delivery_address', 'delivery_city', 'delivery_state',
                       'delivery_postal_code', 'delivery_country', 'delivery_notes'),
            'description': 'Snapshot at order time'
        }),
        ('Payment (Snapshot)', {
            'fields': ('payment_method', 'card_type', 'card_last_four', 'payment_status'),
            'description': 'Snapshot at order time'
        }),
    )
```

---

## API Response Example

```json
{
  "order_number": "ABC123XYZ",
  "market": "US",
  "status": "delivered",

  "references": {
    "shipping_address_id": 15,
    "payment_method_id": 7
  },

  "snapshot": {
    "customer": {
      "name": "John Doe",
      "phone": "+1234567890",
      "email": "john@example.com"
    },
    "delivery": {
      "address": "123 Main Street, Apt 4B",
      "city": "New York",
      "state": "NY",
      "postal_code": "10001",
      "country": "United States",
      "notes": "Leave at door"
    },
    "payment": {
      "method": "card",
      "card_type": "visa",
      "card_last_four": "1234",
      "status": "paid"
    }
  },

  "pricing": {
    "subtotal": "49.99",
    "shipping": "5.99",
    "tax": "0.00",
    "total": "55.98",
    "currency": "$",
    "currency_code": "USD"
  }
}
```

---

## Best Practices

### ✅ Do This

```python
# Always provide references when available
order = Order.objects.create(
    user=user,
    shipping_address=selected_address,  # ✅
    payment_method_used=selected_payment,  # ✅
    # Snapshots auto-filled
)

# Let the save() method handle snapshotting
# Don't manually copy unless needed
```

### ❌ Avoid This

```python
# Don't forget to include references
order = Order.objects.create(
    user=user,
    # shipping_address=None,  # ❌ Missing reference
    delivery_address="123 Main St",  # Only snapshot, no tracking
)

# Don't modify snapshot fields after creation
order.delivery_address = "New address"  # ❌ Breaks immutability
order.save()
```

---

## Migration

```bash
✅ orders/migrations/0004_order_card_last_four_order_card_type_and_more.py

Changes:
+ Add field card_last_four to order
+ Add field card_type to order
+ Add field delivery_country to order
+ Add field delivery_postal_code to order
+ Add field delivery_state to order
+ Add field payment_method_used to order (ForeignKey)
+ Add field shipping_address to order (ForeignKey)
~ Alter field payment_method on order (added 'digital_wallet' choice)
```

---

## Summary

✅ **References** - Track which address/payment was used
✅ **Snapshots** - Preserve data even if references are deleted
✅ **Auto-population** - `save()` method copies data automatically
✅ **Market-aware** - Different fields for KG vs US orders
✅ **Data integrity** - Orders never lose critical information
✅ **Purchase history** - Users can see their past orders
✅ **Analytics** - Track popular addresses/payments
✅ **Quick reorder** - Reuse same address/payment if available

This pattern is **industry standard** for e-commerce platforms! 🛒

---

**Related Documentation:**

- [Order Market Field](ORDER_MARKET_FIELD.md)
- [User Market Fields](USER_MARKET_FIELDS.md)
- [Single Database Architecture](SINGLE_DATABASE_ARCHITECTURE.md)
