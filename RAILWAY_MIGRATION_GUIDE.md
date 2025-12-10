# 🚂 Running Migrations on Railway

## ❌ Why `railway run` Doesn't Work

The `railway run` command **doesn't actually run on Railway's server**. It runs **locally** on your machine but uses Railway's environment variables. That's why you're getting the psycopg2 architecture error (your local Mac is ARM64, but Railway needs x86_64).

---

## ✅ Correct Ways to Run Migrations on Railway

### Method 1: Railway Dashboard (Easiest) ⭐

1. **Go to Railway Dashboard**

   - Visit: https://railway.app
   - Login to your account
   - Select your project

2. **Open Your Service**

   - Click on your Django service
   - Go to the **"Deployments"** tab or **"Settings"** tab

3. **Open Shell/Terminal**

   - Look for **"Shell"** or **"Terminal"** button
   - Or go to **"Settings"** → **"Service"** → **"Shell"**

4. **Run Migration Command**

   ```bash
   python manage.py migrate store_manager
   ```

5. **Or Run All Migrations**
   ```bash
   python manage.py migrate
   ```

---

### Method 2: Railway CLI (Remote Shell)

If Railway CLI supports remote shell:

```bash
# Connect to Railway shell
railway shell

# Then run migration
python manage.py migrate store_manager
```

**Note:** Not all Railway CLI versions support this. Check with `railway --help`.

---

### Method 3: Add Migration to Deploy Script

You can add migrations to your deployment process:

1. **Create/Update `railway.json` or deployment script:**

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python manage.py migrate && python manage.py runserver 0.0.0.0:$PORT"
  }
}
```

Or add to your `Procfile`:

```
web: python manage.py migrate && python manage.py runserver 0.0.0.0:$PORT
```

**⚠️ Warning:** This runs migrations on every deploy. Only do this if you're comfortable with that.

---

### Method 4: Railway One-Click Deploy with Migrations

Some Railway setups allow you to run migrations as a separate step:

1. Go to your service
2. Look for **"Run Command"** or **"One-off Tasks"**
3. Run: `python manage.py migrate store_manager`

---

## 🔍 Check Migration Status First

Before running migrations, you can check what needs to be applied:

```bash
python manage.py showmigrations store_manager
```

You should see:

```
store_manager
 [X] 0001_initial
 [X] 0002_initial
 [ ] 0003_storemanager_store  ← This one needs to be applied
```

---

## 📋 Step-by-Step: Railway Dashboard Method

### Step 1: Access Railway Dashboard

1. Go to https://railway.app
2. Login
3. Select your project

### Step 2: Open Service Terminal

1. Click on your Django service
2. Look for **"Shell"**, **"Terminal"**, or **"Console"** button
3. Click it to open a terminal

### Step 3: Run Migration

```bash
# Check status first
python manage.py showmigrations store_manager

# Run the migration
python manage.py migrate store_manager

# Verify it worked
python manage.py showmigrations store_manager
```

### Step 4: Verify

You should see:

```
Operations to perform:
  Apply all migrations: store_manager
Running migrations:
  Applying store_manager.0003_storemanager_store... OK
```

---

## ⚠️ Important Notes

1. **Backup First**: Always backup your production database before running migrations
2. **Test Locally**: Make sure migrations work locally first (✅ already done)
3. **Check Dependencies**: Make sure all migrations are in order
4. **Monitor Logs**: Watch Railway logs during migration

---

## 🐛 Troubleshooting

### If Migration Fails:

1. **Check Database Connection**

   ```bash
   python manage.py dbshell
   ```

2. **Check Migration File Exists**

   ```bash
   ls store_manager/migrations/0003_storemanager_store.py
   ```

3. **Check for Conflicts**
   ```bash
   python manage.py showmigrations
   ```

### If You Get Permission Errors:

- Make sure you're using the correct Railway account
- Check service permissions
- Verify database credentials

---

## ✅ After Migration

1. **Refresh Django Admin** - Error should be gone
2. **Check StoreManager Admin** - Should show `store` field
3. **Test Store Admin** - Should work without errors

---

## 📝 Quick Reference

**Command to run on Railway:**

```bash
python manage.py migrate store_manager
```

**Where to run it:**

- Railway Dashboard → Your Service → Shell/Terminal

**NOT:**

- ❌ `railway run` (runs locally, not on server)
- ❌ Local terminal (won't affect production)

---

**Ready?** Go to Railway Dashboard and run the migration!
