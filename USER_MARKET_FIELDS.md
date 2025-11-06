# User Market Fields - Market-Specific Services 🌍

## Overview

All user-related models now have **direct `market` fields** that auto-populate from the user's market. This enables market-specific services, validation, and business logic.

---

## Why Market Fields in User Models?

Different markets have fundamentally different:

| Service Type         | KG Market                 | US Market                       |
| -------------------- | ------------------------- | ------------------------------- |
| **SMS Provider**     | Local (Beeline, MegaCom)  | International (Twilio, AWS SNS) |
| **Payment Gateway**  | Local banks, MIR cards    | Stripe, PayPal, Amex            |
| **Address Format**   | City, Building, Apartment | Street, City, State, ZIP        |
| **Delivery Service** | Local couriers            | USPS, FedEx, UPS                |
| **Currency**         | KGS (Som)                 | USD (Dollar)                    |
| **Language**         | Russian, Kyrgyz           | English                         |

---

## Models Updated

### 1. VerificationCode - SMS Provider Routing

**Purpose:** Different SMS providers for different markets

```python
class VerificationCode(models.Model):
    phone = models.CharField(max_length=20)
    code = models.CharField(max_length=6)
    market = models.CharField(max_length=2, choices=MARKET_CHOICES, default='KG')
    # ... other fields
```

**Market-Specific Logic:**

```python
# SMS Provider Selection
def send_verification_code(phone, code, market):
    if market == 'KG':
        # Use local SMS provider (cheaper, faster for KG)
        provider = KyrgyzstanSMSProvider()  # e.g., Beeline API
        provider.send(phone, f"Ваш код: {code}")
    else:  # US market
        # Use international provider
        provider = TwilioSMSProvider()
        provider.send(phone, f"Your code: {code}")
```

**Benefits:**

- ✅ **Cost Optimization** - Local providers are cheaper for KG
- ✅ **Reliability** - Local providers work better in KG
- ✅ **Language** - Different message templates

---

### 2. Address - Format Validation & Delivery

**Purpose:** Different address formats and delivery services

```python
class Address(models.Model):
    user = models.ForeignKey(User, ...)
    market = models.CharField(max_length=2, choices=MARKET_CHOICES, default='KG')
    title = models.CharField(max_length=100)
    full_address = models.TextField()
    street = models.CharField(max_length=255, null=True, blank=True)
    building = models.CharField(max_length=50, null=True, blank=True)
    apartment = models.CharField(max_length=50, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)  # For US
    postal_code = models.CharField(max_length=20, null=True, blank=True)
    country = models.CharField(max_length=100)
    # ... other fields

    def save(self, *args, **kwargs):
        # Auto-populate market and country from user
        if not self.pk and self.user:
            self.market = self.user.market
            self.country = 'Kyrgyzstan' if self.market == 'KG' else 'United States'
        super().save(*args, **kwargs)
```

**Market-Specific Logic:**

#### KG Address Format

```python
# Kyrgyzstan addresses
{
    "title": "Home",
    "city": "Bishkek",
    "building": "12",
    "apartment": "45",
    "full_address": "г. Бишкек, микрорайон 6, дом 12, кв. 45",
    "postal_code": "720000",  # Optional
    "state": None,  # Not used in KG
    "country": "Kyrgyzstan"
}
```

#### US Address Format

```python
# US addresses
{
    "title": "Home",
    "street": "123 Main Street",
    "city": "New York",
    "state": "NY",
    "postal_code": "10001",  # Required (ZIP code)
    "apartment": "Apt 4B",  # Optional
    "building": None,  # Not typically used in US
    "country": "United States"
}
```

**Validation Example:**

```python
from rest_framework import serializers

class AddressSerializer(serializers.ModelSerializer):
    def validate(self, data):
        market = data.get('market') or self.instance.market

        if market == 'KG':
            # KG validation
            if not data.get('city'):
                raise ValidationError("City is required for KG addresses")
            # Postal code optional for KG

        elif market == 'US':
            # US validation
            if not data.get('state'):
                raise ValidationError("State is required for US addresses")
            if not data.get('postal_code'):
                raise ValidationError("ZIP code is required for US addresses")
            # Validate ZIP code format
            if not re.match(r'^\d{5}(-\d{4})?$', data.get('postal_code', '')):
                raise ValidationError("Invalid ZIP code format")

        return data
```

**Delivery Service Selection:**

```python
def calculate_shipping_cost(address):
    if address.market == 'KG':
        # Local courier service
        courier = LocalKGCourier()
        base_cost = 100  # KGS

        # City-based pricing
        if address.city == 'Bishkek':
            return base_cost
        elif address.city in ['Osh', 'Jalal-Abad']:
            return base_cost + 50
        else:
            return base_cost + 100

    else:  # US market
        # Calculate with USPS/FedEx
        courier = USPSShipping()
        base_cost = 5.99  # USD

        # Calculate based on ZIP code zone
        zone = courier.calculate_zone(address.postal_code)
        return base_cost + (zone * 2)
```

---

### 3. PaymentMethod - Gateway Selection

**Purpose:** Different payment gateways and card types

```python
class PaymentMethod(models.Model):
    PAYMENT_TYPE_CHOICES = [
        ('card', 'Credit/Debit Card'),
        ('cash', 'Cash on Delivery'),
        ('bank_transfer', 'Bank Transfer'),  # Popular in KG
        ('digital_wallet', 'Digital Wallet'),
    ]

    CARD_TYPE_CHOICES = [
        ('visa', 'Visa'),
        ('mastercard', 'Mastercard'),
        ('mir', 'MIR'),  # Only KG market
        ('amex', 'American Express'),  # More common in US
        ('other', 'Other'),
    ]

    user = models.ForeignKey(User, ...)
    market = models.CharField(max_length=2, choices=MARKET_CHOICES, default='KG')
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)
    card_type = models.CharField(max_length=20, choices=CARD_TYPE_CHOICES)
    # ... other fields

    def save(self, *args, **kwargs):
        # Auto-populate market from user
        if not self.pk and self.user:
            self.market = self.user.market
        super().save(*args, **kwargs)
```

**Market-Specific Logic:**

#### Payment Gateway Selection

```python
def process_payment(payment_method, amount):
    if payment_method.market == 'KG':
        # KG Payment Gateway
        if payment_method.card_type == 'mir':
            gateway = MIRPaymentGateway()  # MIR cards only work in KG
            currency = 'KGS'
        else:
            gateway = KGLocalBankGateway()  # e.g., Demir Bank, KICB
            currency = 'KGS'

        # Convert to KGS if needed
        amount_kgs = amount if currency == 'KGS' else amount * 84  # USD to KGS

    else:  # US market
        # US Payment Gateway
        if payment_method.card_type == 'amex':
            gateway = StripeAmexGateway()
        else:
            gateway = StripeGateway()  # or PayPal

        currency = 'USD'
        amount_usd = amount

    # Process payment
    result = gateway.charge(
        payment_method=payment_method,
        amount=amount_kgs if payment_method.market == 'KG' else amount_usd,
        currency=currency
    )

    return result
```

#### Available Payment Methods by Market

```python
def get_available_payment_methods(market):
    """Get payment methods available for market"""

    common = [
        ('card', 'Credit/Debit Card'),
        ('cash', 'Cash on Delivery'),
    ]

    if market == 'KG':
        return common + [
            ('bank_transfer', 'Bank Transfer'),  # Very popular in KG
            ('digital_wallet', 'MBank/Элсом'),
        ]
    else:  # US
        return common + [
            ('digital_wallet', 'PayPal/Apple Pay'),
        ]

def get_available_card_types(market):
    """Get card types available for market"""

    common = [
        ('visa', 'Visa'),
        ('mastercard', 'Mastercard'),
    ]

    if market == 'KG':
        return common + [
            ('mir', 'MIR'),  # Russian payment system
        ]
    else:  # US
        return common + [
            ('amex', 'American Express'),
            ('discover', 'Discover'),
        ]
```

---

### 4. Notification - Localized Messaging

**Purpose:** Market-specific notification formatting

```python
class Notification(models.Model):
    user = models.ForeignKey(User, ...)
    market = models.CharField(max_length=2, choices=MARKET_CHOICES, default='KG')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    # ... other fields

    def save(self, *args, **kwargs):
        # Auto-populate market from user
        if not self.pk and self.user:
            self.market = self.user.market
        super().save(*args, **kwargs)
```

**Market-Specific Logic:**

```python
def create_order_notification(order):
    """Create localized order notification"""

    user = order.user
    market = user.market
    language = user.language

    if market == 'KG':
        # Kyrgyzstan notification
        if language == 'ru':
            title = f"Заказ #{order.order_number} оформлен"
            message = f"Ваш заказ на сумму {order.total_amount} сом успешно оформлен"
        else:  # Kyrgyz
            title = f"Буюртма #{order.order_number} кабыл алынды"
            message = f"Сиздин {order.total_amount} сом буюртмаңыз ийгиликтүү кабыл алынды"

        # Add local courier info
        if order.delivery_service:
            message += f"\nКурьер: {order.delivery_service.name_ru}"

    else:  # US market
        # US notification (English)
        title = f"Order #{order.order_number} Confirmed"
        message = f"Your order for ${order.total_amount} has been confirmed"

        # Add USPS tracking if available
        if order.tracking_number:
            message += f"\nTracking: {order.tracking_number}"

    Notification.objects.create(
        user=user,
        market=market,
        type='order',
        title=title,
        message=message,
        order_id=order.id
    )
```

---

## Auto-Population Logic

All models auto-populate the market field from the user:

```python
# Example: Creating an address
user = User.objects.get(phone='+996505123456')  # KG user
print(user.market)  # 'KG'

address = Address.objects.create(
    user=user,
    title="Home",
    city="Bishkek",
    # market='KG' is automatically set!
    # country='Kyrgyzstan' is automatically set!
    ...
)

print(address.market)  # 'KG'
print(address.country)  # 'Kyrgyzstan'
```

---

## Performance Benefits

Direct market fields enable fast filtering:

```python
# Fast queries without JOINs

# Get all KG addresses
kg_addresses = Address.objects.filter(market='KG')

# Get all US payment methods
us_payments = PaymentMethod.objects.filter(market='US')

# Get recent KG notifications
kg_notifs = Notification.objects.filter(
    market='KG',
    is_read=False
).order_by('-created_at')[:10]

# OLD WAY (slower - requires JOIN):
# kg_addresses = Address.objects.filter(user__market='KG')
```

---

## API Examples

### Get User's Addresses

```python
from rest_framework.views import APIView
from rest_framework.response import Response

class UserAddressesView(APIView):
    def get(self, request):
        user = request.user

        # Get addresses for user's market
        addresses = Address.objects.filter(
            user=user,
            market=user.market  # Ensures consistency
        ).order_by('-is_default')

        serializer = AddressSerializer(addresses, many=True)
        return Response(serializer.data)
```

### Get Available Payment Methods

```python
class PaymentMethodOptionsView(APIView):
    def get(self, request):
        market = request.user.market

        # Return market-specific payment options
        payment_types = get_available_payment_methods(market)
        card_types = get_available_card_types(market)

        return Response({
            'market': market,
            'payment_types': payment_types,
            'card_types': card_types,
        })
```

### Send Verification Code

```python
class SendVerificationCodeView(APIView):
    def post(self, request):
        phone = request.data.get('phone')

        # Detect market from phone
        market = 'KG' if phone.startswith('+996') else 'US'

        # Generate code
        code = generate_otp()

        # Save with market
        verification = VerificationCode.objects.create(
            phone=phone,
            code=code,
            market=market,
            expires_at=timezone.now() + timedelta(minutes=5)
        )

        # Send via market-specific provider
        send_verification_code(phone, code, market)

        return Response({'message': 'Code sent'})
```

---

## Database Indexes

Optimized indexes for market-based queries:

```python
# Address
class Meta:
    indexes = [
        models.Index(fields=['user', 'market']),
    ]

# PaymentMethod
class Meta:
    indexes = [
        models.Index(fields=['user', 'market']),
    ]

# Notification
class Meta:
    indexes = [
        models.Index(fields=['market', '-created_at']),
    ]

# VerificationCode
class Meta:
    indexes = [
        models.Index(fields=['market', '-created_at']),
    ]
```

---

## Migration Applied

```bash
✅ users/migrations/0002_address_market_address_state_notification_market_and_more.py

Changes:
+ Add field market to address
+ Add field state to address (for US addresses)
+ Add field market to notification
+ Add field market to paymentmethod
+ Add field market to verificationcode
+ Update PAYMENT_TYPE_CHOICES (added bank_transfer, digital_wallet)
+ Update CARD_TYPE_CHOICES (added amex)
+ Create optimized indexes for market filtering
```

---

## Complete Market Architecture

| Model                | Market Field | Auto-Set   | Purpose                   |
| -------------------- | ------------ | ---------- | ------------------------- |
| **User**             | ✅ Direct    | From phone | User's market             |
| **VerificationCode** | ✅ Direct    | Manual     | SMS provider routing      |
| **Address**          | ✅ Direct ✨ | From user  | Address format & delivery |
| **PaymentMethod**    | ✅ Direct ✨ | From user  | Payment gateway selection |
| **Notification**     | ✅ Direct ✨ | From user  | Localized messaging       |
| **Product**          | ✅ Direct    | Manual     | Product availability      |
| **Category**         | ✅ Direct    | Manual     | Category availability     |
| **Banner**           | ✅ Direct    | Manual     | Banner visibility         |
| **Order**            | ✅ Direct ✨ | From user  | Order market              |
| **RevenueSnapshot**  | ✅ Direct    | Calculated | Revenue tracking          |

---

## Summary

✅ **Added** direct `market` fields to 4 user models
✅ **Auto-populates** from user.market on creation
✅ **Enables** market-specific business logic:

- SMS provider selection (VerificationCode)
- Address format validation (Address)
- Payment gateway routing (PaymentMethod)
- Localized notifications (Notification)
  ✅ **Optimized** with database indexes
  ✅ **Improves** query performance (no JOINs)
  ✅ **Consistent** with other market-aware models

---

**Related Documentation:**

- [Order Market Field](ORDER_MARKET_FIELD.md)
- [Single Database Architecture](SINGLE_DATABASE_ARCHITECTURE.md)
- [Market Filtering Guide](MARKET_FILTERING_GUIDE.md)
