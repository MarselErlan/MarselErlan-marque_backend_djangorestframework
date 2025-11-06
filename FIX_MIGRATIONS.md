# 🔧 Fix Migration Inconsistency

## Problem

```
Migration admin.0001_initial is applied before its dependency
users.0001_initial on database 'default'.
```

## Solution: Clear Migration History in Database

### Option 1: Using Django Shell (Recommended)

```bash
python manage.py shell
```

Then run this Python code:

```python
from django.db import connection

# Delete all migration records
with connection.cursor() as cursor:
    cursor.execute("DELETE FROM django_migrations WHERE app IN ('admin', 'auth', 'contenttypes', 'sessions')")
    cursor.execute("COMMIT")

print("✅ Migration history cleared!")
```

Exit shell: `exit()`

### Option 2: Using psql (PostgreSQL)

```bash
# Connect to database
PGPASSWORD=uQriiHAzwLASuXsFbUewIREtffYGZzlM psql -h shuttle.proxy.rlwy.net -p 13569 -U postgres -d railway

# Clear migration records
DELETE FROM django_migrations WHERE app IN ('admin', 'auth', 'contenttypes', 'sessions');

# Exit
\q
```

### Option 3: Drop All Tables (Clean Start)

⚠️ **WARNING: This deletes all data!**

```bash
python manage.py shell
```

```python
from django.db import connection

with connection.cursor() as cursor:
    # Get all tables
    cursor.execute("""
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public'
    """)
    tables = cursor.fetchall()

    # Drop all tables
    for table in tables:
        cursor.execute(f'DROP TABLE IF EXISTS "{table[0]}" CASCADE')

    cursor.execute("COMMIT")

print("✅ All tables dropped!")
```

---

## After Clearing History

### Step 1: Apply Migrations Fresh

```bash
python manage.py migrate
```

Expected output:

```
Operations to perform:
  Apply all migrations: admin, auth, banners, contenttypes, orders, products, sessions, store_manager, users
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying contenttypes.0002_remove_content_type_name... OK
  Applying auth.0001_initial... OK
  ... (all migrations)
```

### Step 2: Create Superuser

```bash
python manage.py createsuperuser
```

### Step 3: Verify

```bash
python manage.py showmigrations
```

All should show `[X]`.

---

## Quick Command Sequence

```bash
# 1. Clear migration history
python manage.py shell
# (paste Python code from Option 1)

# 2. Apply migrations
python manage.py migrate

# 3. Create superuser
python manage.py createsuperuser

# 4. Done!
python manage.py runserver
```

---

## Alternative: Use Fresh Database

If Railway database can be reset:

1. Delete the database in Railway dashboard
2. Create new database
3. Update `.env` with new credentials
4. Run `python manage.py migrate`
5. Run `python manage.py createsuperuser`

---

**Choose the option that works best for your situation!**
