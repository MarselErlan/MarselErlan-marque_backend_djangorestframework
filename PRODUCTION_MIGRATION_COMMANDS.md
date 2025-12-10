# 🚀 Production Migration Commands

## Quick Copy-Paste Commands for Railway

### Option 1: Single Command (Recommended)

```bash
python manage.py migrate store_manager
```

### Option 2: Run All Pending Migrations

```bash
python manage.py migrate
```

### Option 3: Check Status First, Then Migrate

```bash
# Check what needs to be migrated
python manage.py showmigrations store_manager

# Run the migration
python manage.py migrate store_manager

# Verify it worked
python manage.py showmigrations store_manager
```

---

## How to Run on Railway

### Method 1: Railway Dashboard (Recommended) ⭐

**⚠️ Important:** `railway run` runs **locally** on your machine, not on Railway's server!

**Correct way:**

1. Go to Railway Dashboard: https://railway.app
2. Select your project → Your Django service
3. Click **"Shell"** or **"Terminal"** button
4. Run: `python manage.py migrate store_manager`

### Method 2: Railway Dashboard

1. Go to your Railway project dashboard
2. Click on your service
3. Open the **"Shell"** or **"Deploy Logs"** tab
4. Run: `python manage.py migrate store_manager`

### Method 3: SSH (if available)

```bash
ssh your-railway-instance
cd /app  # or your project directory
python manage.py migrate store_manager
```

---

## Expected Output

You should see:

```
Operations to perform:
  Apply all migrations: store_manager
Running migrations:
  Applying store_manager.0003_storemanager_store... OK
```

---

## Verification

After running, verify with:

```bash
python manage.py showmigrations store_manager
```

Should show:

```
store_manager
 [X] 0001_initial
 [X] 0002_initial
 [X] 0003_storemanager_store  ← All checked!
```

---

## What This Migration Does

- ✅ Adds `store_id` column to `store_managers` table
- ✅ Links StoreManager to Store (nullable ForeignKey)
- ✅ Safe to run (only adds column, doesn't modify existing data)
- ✅ No downtime required

---

## After Migration

1. **Refresh Django Admin** - Error should be gone
2. **Check StoreManager** - Should show `store` field
3. **Test Store Admin** - Should work without errors

---

**Ready to run?** Copy the command and run it on your production server!
