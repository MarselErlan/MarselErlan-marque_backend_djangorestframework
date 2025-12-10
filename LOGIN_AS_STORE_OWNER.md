# 🔐 How to Login as Store Owner (Not Superuser)

## Current Situation

You're currently logged in as **superuser** (`3128059851`), which shows you ALL stores and ALL products.

To see the **store owner view** (filtered to only their stores), you need to login as a **store owner account**.

---

## 🎯 Step-by-Step: Login as Store Owner

### Option 1: Create Store Owner Account via Admin (Recommended)

#### Step 1: Create User Account

1. **While logged in as superuser**, go to:

   - **"AUTHENTICATION AND AUTHORIZATION"** → **"Users"**
   - Click **"ADD USER +"**

2. **Fill in user details:**

   - **Phone:** `+996555111111` (or any phone number)
   - **Password:** Set a password
   - **Password confirmation:** Re-enter password
   - **Full name:** `Store Owner Test`
   - **Location:** `KG` or `US`

3. **IMPORTANT:** Check these boxes:

   - ✅ **"Staff status"** (REQUIRED for admin access!)
   - ❌ **"Superuser status"** (Leave unchecked - this is a regular store owner)

4. Click **"Save"**

#### Step 2: Create Store for This User

1. Go to **"STORES"** → **"Stores"**
2. Click **"ADD STORE +"**
3. Fill in store details:
   - **Name:** `Test Store`
   - **Owner:** Select the user you just created
   - **Market:** `KG` or `US`
   - **Status:** `Pending Approval` (or `Active` if you want it active immediately)
   - **Is active:** ✅ Checked
4. Click **"Save"**

#### Step 3: Logout and Login as Store Owner

1. Click **"LOG OUT"** (top right)
2. Login with:
   - **Username:** `+996555111111` (the phone number you used)
   - **Password:** The password you set
3. You'll now see the **store owner view**!

---

### Option 2: Use Django Shell (Quick Method)

Run this command to create a store owner:

```bash
python manage.py shell
```

Then run:

```python
from users.models import User
from stores.models import Store

# Create store owner user
store_owner = User.objects.create_user(
    phone='+996555222222',
    password='storeowner123',
    full_name='Store Owner',
    location='KG',
    is_staff=True,  # REQUIRED for admin access
    is_active=True
)

# Create store for this user
store = Store.objects.create(
    name='My Store',
    owner=store_owner,
    market='KG',
    status='active',
    is_active=True
)

print(f"Store owner created: {store_owner.phone}")
print(f"Store created: {store.name}")
print(f"Login with phone: {store_owner.phone}, password: storeowner123")
```

Then logout and login with:

- **Username:** `+996555222222`
- **Password:** `storeowner123`

---

## 🔍 What's Different: Superuser vs Store Owner

### **As Superuser (Current):**

- ✅ See ALL stores (from all owners)
- ✅ See ALL products (from all stores)
- ✅ Can use admin actions (approve, suspend, verify)
- ✅ Can change store ownership
- ✅ Full access to everything

### **As Store Owner:**

- ✅ See ONLY your stores
- ✅ See ONLY products from your stores
- ❌ Cannot see other stores' products
- ❌ Cannot use admin actions
- ❌ Cannot change store ownership
- ✅ Can create/edit/delete your own products
- ✅ Can manage your store information

---

## 🧪 Quick Test: Create Test Store Owner

I can create a test store owner account for you. Would you like me to:

1. **Create a test store owner via Django shell?**
2. **Show you the exact commands to run?**

Or you can do it manually:

### Manual Steps:

1. **Logout** from current superuser session
2. **Create new user** via admin (as superuser) with `is_staff=True` but `is_superuser=False`
3. **Create store** and assign to that user
4. **Login** as that user
5. **See filtered view** - only your stores and products

---

## 📋 Quick Reference

### **To Switch to Store Owner View:**

1. **Logout** → Click "LOG OUT" (top right)
2. **Create store owner** (if doesn't exist):
   - User with `is_staff=True`
   - Store owned by that user
3. **Login** with store owner credentials
4. **Navigate** to "STORES" → "Stores"
5. **See only your stores!**

### **Current Login Info:**

- **Superuser:** `3128059851` (you're logged in as this)
- **Store Owner:** Need to create one (see steps above)

---

## ✅ Verification

After logging in as store owner, you should see:

1. **Stores List:**

   - Only stores you own
   - "ADD STORE +" button works
   - Can create new stores (you become owner)

2. **Products List:**

   - Only products from your stores
   - "ADD PRODUCT +" button works
   - Can create products for your stores

3. **No Admin Actions:**
   - No "Approve", "Suspend", "Verify" actions
   - These are only for superusers

---

**Ready to test?** Create a store owner account and login to see the filtered view!
