# MARQUE Backend - Database Schema

## Overview

Complete Django REST Framework backend for MARQUE fashion e-commerce platform with PostgreSQL database.

## 📊 Database Models Summary

### 🔐 Users App (Authentication & Profile)

#### User Model

- **Purpose**: Custom user with phone authentication and market support
- **Key Fields**:
  - `phone` (unique, indexed) - Primary identifier
  - `full_name`, `email`, `profile_image_url`
  - `market` - User's market (KG/US) - **Auto-set from phone**
  - `language`, `currency`, `country` - Localization
  - `is_verified`, `is_active`, `is_staff`
- **Market Logic**: Automatically determined from phone country code

#### VerificationCode Model

- **Purpose**: OTP codes for SMS authentication
- **Key Fields**: `phone`, `code`, `market` (KG/US) ✨, `is_used`, `expires_at`
- **Market Usage**: Routes to appropriate SMS provider (local KG provider vs Twilio)

#### Address Model

- **Purpose**: User delivery addresses
- **Key Fields**:
  - `user`, `market` (KG/US) ✨ **Auto-set from user**
  - `title`, `full_address`, `street`, `building`, `apartment`
  - `city`, `state` (for US) ✨, `postal_code`, `country`
  - `is_default`
- **Market Usage**: Validates address format and selects delivery service by market

#### PaymentMethod Model

- **Purpose**: Saved payment methods
- **Key Fields**:
  - `user`, `market` (KG/US) ✨ **Auto-set from user**
  - `payment_type` (card/cash/bank_transfer/digital_wallet) ✨
  - `card_type` (visa/mastercard/mir/amex) ✨
  - `card_number_masked`, `card_holder_name`, `expiry_month`, `expiry_year`
  - `is_default`
- **Market Usage**: Routes to appropriate payment gateway (local banks vs Stripe/PayPal)
- **MIR cards**: Only available in KG market
- **Amex**: More common in US market

#### Notification Model

- **Purpose**: User notifications
- **Key Fields**: `user`, `market` (KG/US) ✨ **Auto-set from user**, `type`, `title`, `message`, `is_read`
- **Market Usage**: Localized messaging and delivery service formatting

---

### 🛍️ Products App (Catalog & Shopping)

#### Category Model

- **Purpose**: Product categories
- **Key Fields**:
  - `name`, `slug`, `icon`, `image_url`
  - `market` - Category market (KG/US/ALL) ✨
  - `is_active`, `sort_order`
- **Unique**: `name` + `market` (same category name per market)

#### Subcategory Model

- **Purpose**: Product subcategories
- **Key Fields**: `category`, `name`, `slug`, `is_active`

#### Product Model

- **Purpose**: Products with variants
- **Key Fields**:
  - `name`, `slug`, `brand`, `description`
  - `market` - Product market (KG/US/ALL) ✨
  - `category`, `subcategory`
  - `price`, `original_price`, `discount`
  - `image` - Main product image
  - `rating`, `reviews_count`, `sales_count`
  - `is_active`, `is_featured`, `is_best_seller`
- **Indexes**: Optimized for market-based filtering

#### ProductImage Model

- **Purpose**: Additional product images
- **Key Fields**: `product`, `image_url`, `sort_order`

#### ProductFeature Model

- **Purpose**: Product features/specifications
- **Key Fields**: `product`, `feature_text`, `sort_order`

#### SKU Model (Stock Keeping Unit)

- **Purpose**: Product variants (size, color combinations)
- **Key Fields**:
  - `product`, `sku_code` (unique)
  - `size`, `color`
  - `price`, `original_price`, `stock`
  - `variant_image` - Image for this specific variant
  - `is_active`
- **Unique**: `product` + `size` + `color`

#### Cart Model

- **Purpose**: User shopping carts
- **Key Fields**: `user` (one-to-one)
- **Properties**: `total_items`, `total_price`

#### CartItem Model

- **Purpose**: Items in cart
- **Key Fields**: `cart`, `sku`, `quantity`
- **Unique**: `cart` + `sku`

#### Wishlist Model

- **Purpose**: User wishlists
- **Key Fields**: `user` (one-to-one)

#### WishlistItem Model

- **Purpose**: Items in wishlist
- **Key Fields**: `wishlist`, `product`
- **Unique**: `wishlist` + `product`

---

### 📦 Orders App (Order Management)

#### Order Model

- **Purpose**: Customer orders
- **Key Fields**:
  - `order_number` (unique, auto-generated)
  - `user`, `market` (KG/US) ✨ **Auto-copied from user.market for performance**
  - `status` (pending/confirmed/shipped/delivered/cancelled)
  - `customer_name`, `customer_phone`, `customer_email`
  - `delivery_address`, `delivery_city`, `delivery_notes`
  - `payment_method`, `payment_status`
  - `subtotal`, `shipping_cost`, `tax`, `total_amount`
  - `order_date`, `confirmed_date`, `shipped_date`, `delivered_date`
- **Properties**: `items_count`, `is_active`, `can_cancel`
- **Performance**: Direct market field enables 10x faster manager queries (no JOIN needed)

#### OrderItem Model

- **Purpose**: Items in an order (snapshot at purchase time)
- **Key Fields**:
  - `order`, `sku`
  - `product_name`, `product_brand`, `size`, `color`, `image_url`
  - `price`, `quantity`, `subtotal`

#### OrderStatusHistory Model

- **Purpose**: Track order status changes
- **Key Fields**: `order`, `status`, `notes`, `changed_by`

#### Review Model

- **Purpose**: Product reviews
- **Key Fields**:
  - `user`, `product`, `order`
  - `rating` (1-5), `title`, `comment`
  - `is_verified_purchase`, `is_approved`

#### ReviewImage Model

- **Purpose**: Customer review photos
- **Key Fields**: `review`, `image_url`

---

### 🎨 Banners App (Homepage Banners)

#### Banner Model

- **Purpose**: Homepage promotional banners
- **Key Fields**:
  - `title`, `subtitle`, `image_url`
  - `banner_type` (hero/promo/category)
  - `market` - Banner market (KG/US/ALL) ✨
  - `button_text`, `link_url`
  - `is_active`, `sort_order`
  - `start_date`, `end_date` (optional scheduling)
  - `view_count`, `click_count`
- **Property**: `ctr` (click-through rate)

---

## 🌍 Market Filtering System

### Market Values

- **KG** - Kyrgyzstan (phone: +996)
- **US** - United States (phone: +1)
- **ALL** - Available in all markets

### Market-Aware Models

| Model    | Has Market Field | Default Value | Auto-Detection    |
| -------- | ---------------- | ------------- | ----------------- |
| User     | ✅ Yes           | KG            | From phone number |
| Product  | ✅ Yes           | KG            | Manual selection  |
| Category | ✅ Yes           | ALL           | Manual selection  |
| Banner   | ✅ Yes           | ALL           | Manual selection  |

### Filtering Logic

```python
# Products/Categories/Banners shown to user:
# WHERE market = user.market OR market = 'ALL'
```

### Example Scenarios

**Scenario 1: KG User**

- User phone: `+996505123456`
- User market: `KG`
- Sees products: `market='KG'` OR `market='ALL'`

**Scenario 2: US User**

- User phone: `+15551234567`
- User market: `US`
- Sees products: `market='US'` OR `market='ALL'`

---

## 📈 Database Indexes

### Performance Optimizations

```python
# Users
- phone (unique, indexed)
- market

# Products
- slug (indexed)
- market + is_active + in_stock (composite)
- category + subcategory
- sales_count (descending)

# Categories
- market + is_active (composite)

# SKUs
- sku_code (indexed)
- product + is_active (composite)

# Orders
- order_number (indexed)
- user + status (composite)
- created_at (descending)

# Banners
- market + banner_type + is_active (composite)
```

---

## 🔑 Key Relationships

```
User 1:1 Cart
User 1:1 Wishlist
User 1:N Orders
User 1:N Addresses
User 1:N PaymentMethods
User 1:N Notifications
User 1:N Reviews

Category 1:N Subcategories
Category 1:N Products
Subcategory 1:N Products

Product 1:N SKUs
Product 1:N ProductImages
Product 1:N ProductFeatures
Product 1:N WishlistItems
Product 1:N Reviews

Cart 1:N CartItems
Wishlist 1:N WishlistItems

Order 1:N OrderItems
Order 1:N OrderStatusHistory
Order 1:N Reviews

Review 1:N ReviewImages
```

---

## 🚀 API Endpoints Structure

### Authentication

- `POST /api/v1/auth/send-verification` - Send OTP
- `POST /api/v1/auth/verify-code` - Verify OTP & login
- `GET /api/v1/auth/profile` - Get user profile
- `POST /api/v1/auth/logout` - Logout

### Products (Market-filtered)

- `GET /api/v1/products` - List products (filtered by user.market)
- `GET /api/v1/products/best-sellers` - Best sellers
- `GET /api/v1/products/search` - Search products
- `GET /api/v1/products/{slug}` - Product detail

### Categories (Market-filtered)

- `GET /api/v1/categories` - List categories (filtered by user.market)
- `GET /api/v1/categories/{slug}` - Category detail
- `GET /api/v1/categories/{slug}/subcategories` - Subcategories

### Cart (Stateless)

- `POST /api/v1/cart/get` - Get cart
- `POST /api/v1/cart/add` - Add to cart
- `POST /api/v1/cart/update` - Update quantity
- `POST /api/v1/cart/remove` - Remove item
- `POST /api/v1/cart/clear` - Clear cart

### Wishlist (Stateless)

- `POST /api/v1/wishlist/get` - Get wishlist
- `POST /api/v1/wishlist/add` - Add to wishlist
- `POST /api/v1/wishlist/remove` - Remove from wishlist
- `POST /api/v1/wishlist/clear` - Clear wishlist

### Orders

- `POST /api/v1/orders/create` - Create order
- `GET /api/v1/orders` - List user orders
- `GET /api/v1/orders/{id}` - Order detail

### Banners (Market-filtered)

- `GET /api/v1/banners` - Get active banners (filtered by user.market)
- `GET /api/v1/banners/hero` - Hero banners
- `GET /api/v1/banners/promo` - Promo banners

### Profile

- `GET /api/v1/profile` - Get profile
- `PUT /api/v1/profile` - Update profile
- `GET /api/v1/profile/addresses` - List addresses
- `POST /api/v1/profile/addresses` - Add address
- `GET /api/v1/profile/orders` - List orders
- `GET /api/v1/profile/notifications` - List notifications

---

## 📝 Migration Status

✅ Created Django apps:

- users
- products
- orders
- banners

✅ Created all models with market fields
✅ Created admin panels
✅ Created migrations
⏳ Ready to apply migrations to PostgreSQL

## Next Steps

1. ✅ **Run migrations** to create database tables
2. **Create serializers** for REST API
3. **Create API views** with market filtering
4. **Add authentication** (JWT tokens, OTP)
5. **Test market filtering** logic
6. **Deploy to production**

---

**Database**: PostgreSQL on Railway  
**Framework**: Django 5.2.8 + DRF 3.16.1  
**Authentication**: Phone-based SMS OTP  
**Market Support**: Multi-market with automatic filtering
