# 🚀 Store Admin Quick Start Guide

## Access Store Admin in 3 Steps

### Step 1: Go to Admin URL

**Production:**

```
https://marquebwithd-production.up.railway.app/admin/
```

**Local Development:**

```
http://localhost:8000/admin/
```

### Step 2: Login

**For Store Owners:**

- Use your phone number as username
- Enter your password
- **Important:** Your account must have `is_staff = True` to access admin

**For Superusers:**

- Use your superuser credentials
- Full access to everything

### Step 3: Navigate to Stores

1. In the **left sidebar**, find **"STORES"** section
2. Click **"Stores"**
3. You'll see your stores (or all stores if superuser)

---

## 🎯 What You Can Do

### **As Store Owner:**

✅ **View Your Stores**

- Click "STORES" → "Stores" in sidebar
- See only stores you own

✅ **Create New Store**

- Click "ADD STORE +" button
- Fill in details
- You automatically become the owner

✅ **Manage Your Products**

- Click "PRODUCTS" → "Products" in sidebar
- See only products from your stores
- Click "ADD PRODUCT +" to create new product

✅ **Edit Store Information**

- Click on store name in the list
- Update store details
- Save changes

### **As Superuser:**

✅ **View All Stores**

- See stores from all owners
- Use filters to find specific stores

✅ **Approve Stores**

- Select stores → Action: "Approve selected stores" → Go
- Changes status to "Active"

✅ **Verify Stores**

- Select stores → Action: "Verify selected stores" → Go
- Adds verified badge

✅ **Manage All Products**

- See products from all stores
- Can edit any product

---

## 🔑 Setting Up Store Owner Access

### **Method 1: Via Django Admin (Superuser Required)**

1. Login as superuser to `/admin/`
2. Go to **"AUTHENTICATION AND AUTHORIZATION"** → **"Users"**
3. Find or create the user
4. Edit user:
   - Check **"Staff status"** ✅ (required!)
   - Save
5. Create store and assign user as owner, OR
6. User can create store via API: `POST /api/v1/stores/register/`

### **Method 2: Via Django Shell**

```python
python manage.py shell

from users.models import User
from stores.models import Store

# Get or create user
user = User.objects.get(phone='+996555123456')
user.is_staff = True
user.save()

# Create store for user
store = Store.objects.create(
    name='My Store',
    owner=user,
    market='KG',
    status='pending',
    is_active=True
)
```

### **Method 3: Via API (User Self-Registration)**

User calls:

```
POST /api/v1/stores/register/
{
    "name": "My Store",
    "market": "KG",
    "description": "Store description"
}
```

Then superuser sets `is_staff = True` for that user.

---

## 📍 Navigation Paths

### **To Manage Stores:**

```
Admin Home → STORES → Stores
```

### **To Manage Products:**

```
Admin Home → PRODUCTS → Products
```

### **To Create New Store:**

```
Admin Home → STORES → Stores → "ADD STORE +" button
```

### **To Create New Product:**

```
Admin Home → PRODUCTS → Products → "ADD PRODUCT +" button
```

---

## ⚠️ Important Notes

1. **Staff Status Required**

   - Users must have `is_staff = True` to access Django admin
   - This is different from store ownership
   - Store owners need both: `is_staff = True` AND own at least one store

2. **Store Status**

   - New stores start as "Pending Approval"
   - Superuser must approve them to become "Active"
   - Only active stores can be used for products

3. **Permissions**
   - Store owners can only see/edit their own data
   - Superusers can see/edit everything
   - Permissions are enforced automatically

---

## 🧪 Test Access

### **Quick Test:**

1. **Login** to `/admin/`
2. **Check Stores** - Should see your stores
3. **Check Products** - Should see products from your stores
4. **Try Creating Product** - Should work if you have active store

If you see "You don't have permission", check:

- User has `is_staff = True`
- User owns at least one store (for store owners)
- Store is active (`is_active = True`)

---

## 📞 Need Help?

**Common Issues:**

- Can't login? → Check `is_staff = True`
- No stores visible? → Check store ownership and `is_active`
- Can't create products? → Check you have active store
- Slug error? → Already fixed! Should work now

---

**Ready to go!** 🎉

Just login to `/admin/` and start managing your stores!
