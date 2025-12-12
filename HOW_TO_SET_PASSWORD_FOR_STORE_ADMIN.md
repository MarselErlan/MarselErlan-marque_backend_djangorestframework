# 🔐 How to Set Password for Store Admin Access

## Problem

Store owners need a password to log in to Django admin (`/admin/`), but the system uses phone-based OTP authentication. When users register through the API, they don't have a password set.

## Solution

There are **3 ways** to set a password for store owners:

---

## Method 1: Set Password via API (Recommended for Store Owners)

Store owners can set their own password through the API:

### Step 1: Login to the main website

- Use your phone number and OTP code to log in normally

### Step 2: Set password via API

Make a POST request to:

```
POST /api/v1/auth/set-password
```

**Headers:**

```
Authorization: Token YOUR_AUTH_TOKEN
Content-Type: application/json
```

**Body:**

```json
{
  "password": "your_secure_password",
  "password_confirm": "your_secure_password"
}
```

**Example using curl:**

```bash
curl -X POST https://your-domain.com/api/v1/auth/set-password \
  -H "Authorization: Token YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "password": "MySecurePassword123!",
    "password_confirm": "MySecurePassword123!"
  }'
```

**Requirements:**

- Password must be at least 8 characters long
- Both password fields must match

### Step 3: Login to Django Admin

1. Go to: `https://your-domain.com/admin/`
2. **Phone:** Your phone number (e.g., `+996555111111`)
3. **Password:** The password you just set
4. Click "Log in"

---

## Method 2: Set Password via Django Admin (Superuser Only)

If you're a superuser, you can set passwords for store owners:

### Step 1: Login as Superuser

1. Go to `/admin/`
2. Login with your superuser credentials

### Step 2: Find the Store Owner

1. Go to **"AUTHENTICATION AND AUTHORIZATION"** → **"Users"**
2. Find the store owner by phone number
3. Click on their name to edit

### Step 3: Set Password

1. Scroll down to the **"Password"** section
2. Click **"Change password"** link
3. Enter the new password
4. Click **"Save"**

### Step 4: Notify Store Owner

Send the password to the store owner securely (via email, SMS, or secure messaging).

---

## Method 3: Set Password via Django Shell

For quick testing or bulk operations:

### Step 1: Open Django Shell

```bash
python manage.py shell
```

### Step 2: Set Password

```python
from users.models import User

# Find the user
user = User.objects.get(phone='+996555111111')

# Set password
user.set_password('NewPassword123!')
user.save()

print(f"Password set for {user.phone}")
```

### Step 3: Exit Shell

```python
exit()
```

---

## Method 4: Set Password via Frontend (Future Enhancement)

We can add a "Set Admin Password" section in the profile page that calls the API endpoint.

---

## Important Notes

1. **Password Requirements:**

   - Minimum 8 characters
   - Can contain letters, numbers, and special characters
   - Django will hash the password automatically

2. **Security:**

   - Never share passwords via insecure channels
   - Encourage store owners to use strong passwords
   - Consider implementing password reset functionality

3. **Store Owner Access:**

   - Store owners must have `is_staff=True` to access admin
   - This is automatically granted when they register a store
   - They can only see their own stores and products

4. **Troubleshooting:**
   - If login fails, verify:
     - User has `is_staff=True`
     - User has an active store
     - Password was set correctly
     - Phone number matches exactly (including country code)

---

## Quick Test

To quickly test store owner admin access:

```bash
# In Django shell
python manage.py shell
```

```python
from users.models import User
from stores.models import Store

# Get or create store owner
user, created = User.objects.get_or_create(
    phone='+996555999888',
    defaults={
        'full_name': 'Test Store Owner',
        'is_staff': True,
        'is_active': True,
        'is_verified': True
    }
)

# Set password
user.set_password('test123456')
user.save()

# Create store for them
store, _ = Store.objects.get_or_create(
    owner=user,
    defaults={
        'name': 'Test Store',
        'slug': 'test-store',
        'market': 'KG',
        'status': 'active',
        'is_active': True
    }
)

print(f"✅ Store owner created!")
print(f"Phone: {user.phone}")
print(f"Password: test123456")
print(f"Admin URL: /admin/")
```

Then login at `/admin/` with:

- **Phone:** `+996555999888`
- **Password:** `test123456`

---

## API Endpoint Details

**Endpoint:** `POST /api/v1/auth/set-password`

**Authentication:** Required (Token)

**Request Body:**

```json
{
  "password": "string (min 8 characters)",
  "password_confirm": "string (must match password)"
}
```

**Success Response (200):**

```json
{
  "success": true,
  "message": "Password set successfully. You can now log in to Django admin."
}
```

**Error Response (400):**

```json
{
  "password": ["This field is required."],
  "password_confirm": ["Passwords do not match."]
}
```

---

## Next Steps

1. **For Store Owners:** Use Method 1 (API) to set your password
2. **For Superusers:** Use Method 2 (Admin) to set passwords for store owners
3. **For Developers:** Consider adding a frontend UI for password management
