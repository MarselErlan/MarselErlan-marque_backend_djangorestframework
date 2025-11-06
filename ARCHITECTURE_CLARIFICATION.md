# Architecture Clarification ✅

## What Was Corrected

The store_manager models and documentation have been updated to clarify the **single database architecture**.

---

## ❌ Previous Misunderstanding

The frontend UI shows "KG DB" and "US DB" which might imply:

- ❌ Two separate PostgreSQL databases
- ❌ Database switching when changing markets
- ❌ Separate connections for KG and US

---

## ✅ Actual Architecture

### **ONE PostgreSQL Database**

All data is stored in a single PostgreSQL database on Railway.

The `market` column is used to **filter** which data to show, not to separate databases.

```
┌─────────────────────────────────────────────┐
│   Single PostgreSQL Database (Railway)      │
│                                             │
│   Products: market='KG' | 'US' | 'ALL'     │
│   Users: market='KG' | 'US'                 │
│   Categories: market='KG' | 'US' | 'ALL'   │
│   Banners: market='KG' | 'US' | 'ALL'      │
│   Revenue: market='KG' | 'US'               │
│                                             │
│   All in ONE database, filtered by column  │
└─────────────────────────────────────────────┘
```

---

## 🔄 What The Market Switcher Really Does

### Frontend UI:

```tsx
<MarketIndicator
  currentMarket={currentMarket} // 'kg' or 'us'
  onMarketChange={handleMarketChange}
  showSwitcher={true}
/>
```

Shows: "KG DB 🇰🇬" or "US DB 🇺🇸"

### What Actually Happens:

1. **Manager clicks switcher**

   ```typescript
   setCurrentMarket("us");
   localStorage.setItem("admin_market", "us");
   ```

2. **Settings updated in database**

   ```python
   manager.settings.active_market = 'US'
   manager.settings.save()
   ```

3. **Queries filtered by market**

   ```python
   # Get orders for US market
   orders = Order.objects.filter(
       user__market='US'  # ← Filter by column
   )

   # Calculate US revenue
   revenue = orders.aggregate(
       total=Sum('total_amount')
   )
   ```

4. **Frontend receives filtered data**
   - Only US market orders
   - Only US market revenue
   - Same database, different filter

---

## 📊 Model Updates

### Updated Models with MARKET_CHOICES:

```python
MARKET_CHOICES = [
    ('KG', 'Kyrgyzstan'),
    ('US', 'United States'),
]
```

Applied to:

- ✅ `ManagerSettings.active_market`
- ✅ `RevenueSnapshot.market`
- ✅ `ManagerActivityLog.market`
- ✅ `DailyReport.market`
- ✅ `ManagerNotification.market`

### Added Clarifying Comments:

```python
class RevenueSnapshot(models.Model):
    """Daily and hourly revenue snapshots for analytics

    Note: All data is stored in ONE database. The 'market'
    field is used to filter/separate analytics by market
    (KG vs US orders from user.market).
    """
```

---

## 🗄️ Database Query Examples

### Customer Queries (Auto-filtered by user.market):

```python
# KG user logs in
user = User.objects.get(phone='+996505...')
user.market  # 'KG'

# Products shown to KG user
products = Product.objects.filter(
    Q(market='KG') | Q(market='ALL'),
    is_active=True
)
```

### Manager Queries (Filtered by active_market):

```python
# Manager switches to US view
manager.settings.active_market = 'US'

# Get US market orders (from same database)
us_orders = Order.objects.filter(
    user__market='US'  # Filter by column
).order_by('-created_at')

# Calculate US revenue (from same database)
us_revenue = us_orders.filter(
    order_date__date=today
).aggregate(
    total=Sum('total_amount')
)
```

---

## 🎯 Key Points

### ✅ What's True:

1. **ONE database** for entire platform
2. **Market column** filters data
3. **Order has direct market field** (copied from user.market) ✨
4. **Manager switcher** changes query filters
5. **All data** stored together
6. **Filter by market** to separate views

### ❌ What's NOT True:

1. ~~Separate databases for KG and US~~
2. ~~Database switching when changing markets~~
3. ~~Different connections for each market~~
4. ~~Data stored in different locations~~

---

## 📋 Benefits of This Approach

### Advantages:

✅ **Simpler Infrastructure** - One database to manage
✅ **Lower Costs** - One connection, one backup
✅ **Easier Migrations** - Apply once
✅ **Better Analytics** - Compare markets easily
✅ **Flexible** - Add new markets easily
✅ **Consistent** - Single source of truth

### Implementation:

✅ **Filter Queries** - Always add market filter
✅ **Index Optimization** - Indexes on market columns
✅ **Manager Permissions** - Control market access
✅ **Revenue Tracking** - Separate snapshots per market
✅ **Activity Logging** - Track market context

---

## 🔧 Updated Files

### Models:

- ✅ `store_manager/models.py` - Added MARKET_CHOICES and clarifying comments

### Migrations:

- ✅ `store_manager/migrations/0002_*.py` - Updated field definitions

### Documentation:

- ✅ `SINGLE_DATABASE_ARCHITECTURE.md` - NEW: Complete architecture guide
- ✅ `README.md` - NEW: Project overview with clarification
- ✅ `ARCHITECTURE_CLARIFICATION.md` - NEW: This file
- ✅ `STORE_MANAGER_GUIDE.md` - Updated with correct info
- ✅ `MODELS_COMPLETE_SUMMARY.md` - Updated with correct info

---

## ✅ Verification

To verify the single database architecture:

```bash
# Check database connection
python manage.py dbshell

# Count total tables
SELECT COUNT(*) FROM information_schema.tables
WHERE table_schema='public';

# See all markets in one products table
SELECT market, COUNT(*)
FROM products
GROUP BY market;

# See all markets in one users table
SELECT market, COUNT(*)
FROM users
GROUP BY market;
```

Result: All data in ONE database, filtered by market column! ✅

---

## 🎓 Remember

**"KG DB" and "US DB" in the UI are just labels for the filtered view.**

**The reality: ONE PostgreSQL database, market-filtered queries.**

This is actually a **better architecture** than separate databases!

---

**Architecture: Clarified and Documented** ✅  
**Models: Updated with correct comments** ✅  
**Migrations: Generated** ✅  
**Ready for API implementation!** 🚀
