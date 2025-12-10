# 🎯 How to Access Store Admin Interface

## Quick Access Guide

### 1. **Access Django Admin**

**URL:** `https://your-domain.com/admin/`

For your production server:

```
https://marquebwithd-production.up.railway.app/admin/
```

For local development:

```
http://localhost:8000/admin/
```

### 2. **Login**

You need to login with:

- **Store Owner Account**: Any user account that owns a store
- **Superuser Account**: Admin account with full access

### 3. **Navigate to Stores**

After logging in, you'll see the Django admin dashboard. In the left sidebar:

1. Find **"STORES"** section
2. Click on **"Stores"** (or "Stores + Add" to create new)
3. You'll see the list of stores you have access to

---

## 🔐 What You'll See Based on Your Role

### **As a Store Owner:**

1. **Stores List**

   - Only see stores you own
   - Can create new stores (you become the owner automatically)
   - Can edit/delete your own stores

2. **Products List**

   - Only see products from your stores
   - Can create new products (assigned to your store)
   - Can edit/delete products from your stores

3. **Limited Access**
   - Cannot see other stores' products
   - Cannot change store ownership
   - Cannot use admin actions (approve, suspend, etc.)

### **As a Superuser:**

1. **Stores List**

   - See ALL stores from all owners
   - Can create stores for any owner
   - Can edit/delete any store
   - Can use admin actions (approve, suspend, verify, feature stores)

2. **Products List**
   - See ALL products from all stores
   - Can create products for any store
   - Can edit/delete any product

---

## 📝 Step-by-Step Instructions

### **For Store Owners:**

#### Step 1: Login

```
1. Go to: https://marquebwithd-production.up.railway.app/admin/
2. Enter your phone number and password
3. Click "Log in"
```

#### Step 2: Access Your Stores

```
1. In left sidebar, find "STORES" section
2. Click "Stores"
3. You'll see only your stores listed
```

#### Step 3: Create New Store (Optional)

```
1. Click "ADD STORE +" button (top right)
2. Fill in store information:
   - Name: Your store name
   - Description: Store description
   - Market: Select market (KG or US)
   - Contact info: Email, phone, website, address
3. Click "Save"
4. Store will be created with status "Pending Approval"
```

#### Step 4: Manage Your Products

```
1. In left sidebar, find "PRODUCTS" section
2. Click "Products"
3. You'll see only products from your stores
4. Click "ADD PRODUCT +" to create new product
5. Select your store from dropdown
6. Fill in product details
7. Click "Save"
```

---

## 🎨 Admin Interface Features

### **Store Management:**

**List View:**

- See all your stores in a table
- Filter by market, status, active/verified/featured
- Search by name, slug, email, phone
- Click on store name to edit

**Create/Edit Store:**

- **Basic Information**: Name, slug (auto-generated), description, owner, market
- **Visual Identity**: Logo, cover image
- **Contact Information**: Email, phone, website, address
- **Status**: Active, verified, featured flags
- **Statistics**: Rating, reviews, orders, products count (read-only)

### **Product Management:**

**List View:**

- See all products from your stores
- Filter by category, brand, active status, stock
- Search by name, brand, description
- Click on product name to edit

**Create/Edit Product:**

- **Basic Information**: Name, slug (auto-generated), description, store, brand
- **Category Structure**: Category, subcategory, second subcategory
- **Pricing**: Price, original price, discount, currency
- **Product Details**: Market, gender, AI description
- **Status**: Active, in stock, featured, best seller
- **SKUs**: Manage product variants (sizes, colors, prices, stock)
- **Images**: Upload product images
- **Features**: Add product features

---

## 🔧 Creating a Store Owner Account

### **Option 1: Via Django Admin (Superuser)**

1. Login as superuser
2. Go to **"AUTHENTICATION AND AUTHORIZATION"** → **"Users"**
3. Click **"ADD USER +"**
4. Enter phone number and password
5. Check **"Staff status"** (required for admin access)
6. Save
7. Create a store and assign this user as owner

### **Option 2: Via API (Store Registration)**

Store owners can register via API:

```
POST /api/v1/stores/register/
```

This automatically:

- Creates the store
- Sets the authenticated user as owner
- Sets status to "Pending Approval"

Then they can login to admin to manage their store.

---

## 🚨 Common Issues & Solutions

### **Issue 1: "You don't have permission to view this page"**

**Solution:**

- Make sure user has `is_staff = True`
- User must own at least one active store (for store owners)
- Or user must be superuser

### **Issue 2: "No stores visible"**

**Solution:**

- Check if user owns any stores
- Check if stores are active (`is_active = True`)
- Superusers should see all stores

### **Issue 3: "Cannot create products"**

**Solution:**

- Make sure user owns at least one active store
- Store must be active (`is_active = True`)

### **Issue 4: "Slug field error"**

**Solution:**

- This is fixed! Slug is now auto-generated when creating
- Slug becomes readonly when editing

---

## 📋 Quick Reference

### **URLs:**

- Admin Login: `/admin/`
- Stores List: `/admin/stores/store/`
- Products List: `/admin/products/product/`
- Create Store: `/admin/stores/store/add/`
- Create Product: `/admin/products/product/add/`

### **Permissions:**

| Action            | Store Owner | Superuser |
| ----------------- | ----------- | --------- |
| View own stores   | ✅          | ✅        |
| View all stores   | ❌          | ✅        |
| Create store      | ✅          | ✅        |
| Edit own store    | ✅          | ✅        |
| Edit any store    | ❌          | ✅        |
| Delete own store  | ✅          | ✅        |
| Delete any store  | ❌          | ✅        |
| View own products | ✅          | ✅        |
| View all products | ❌          | ✅        |
| Create product    | ✅          | ✅        |
| Edit own products | ✅          | ✅        |
| Edit any product  | ❌          | ✅        |
| Admin actions     | ❌          | ✅        |

---

## 🎯 Example Workflow

### **Store Owner Workflow:**

1. **Login** → `/admin/`
2. **Create Store** → "STORES" → "Stores" → "ADD STORE +"
3. **Wait for Approval** → Superuser approves store
4. **Create Products** → "PRODUCTS" → "Products" → "ADD PRODUCT +"
5. **Manage Products** → Edit, add SKUs, upload images
6. **Monitor Store** → View statistics, orders count

### **Superuser Workflow:**

1. **Login** → `/admin/`
2. **Review Stores** → "STORES" → "Stores" → See all stores
3. **Approve Stores** → Select stores → Action: "Approve selected stores" → Go
4. **Verify Stores** → Select stores → Action: "Verify selected stores" → Go
5. **Manage All Products** → "PRODUCTS" → "Products" → See all products

---

## ✅ Verification

To verify everything is working:

1. **Login as store owner**
2. **Check stores list** - Should only see your stores
3. **Check products list** - Should only see products from your stores
4. **Try creating a product** - Should work without errors
5. **Try editing a product** - Slug should be readonly

---

**Status:** ✅ **READY TO USE**

Your Django admin is fully configured for store owners!
