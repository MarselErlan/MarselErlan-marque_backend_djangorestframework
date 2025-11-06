# Store Manager System - Complete Guide

## Overview

The Store Manager system provides a comprehensive admin panel for managing orders, tracking revenue, and overseeing operations across multiple markets (KG and US).

## 🎯 Key Features

### 1. **Multi-Market Support**

- Managers can access KG and/or US markets
- Switch between markets dynamically
- Market-specific order filtering and analytics
- Real-time market indicator showing active database

### 2. **Order Management**

- View today's orders (last 24 hours)
- View all orders (complete history)
- Filter by status: All, Pending, In Transit, Delivered
- Search by order number, phone, or address
- View detailed order information
- Change order status
- Cancel/Resume orders
- Track order history

### 3. **Revenue Analytics**

- Real-time revenue tracking
- Hourly revenue breakdown
- Daily/Weekly/Monthly snapshots
- Compare with previous periods
- Average order value
- Order count metrics
- Revenue change percentages

### 4. **Manager Settings**

- Language selection (Russian, Kyrgyz, English)
- Theme: Light/Dark mode
- Notification preferences:
  - New orders
  - Status changes
  - Daily reports via email
  - Delivery errors
- Dashboard customization

### 5. **Activity Logging**

- All manager actions are logged
- Audit trail for compliance
- Track: logins, order changes, exports, etc.

---

## 📊 Database Models

### StoreManager Model

Manager roles and permissions.

**Fields:**

- `user` - OneToOne with User model
- `role` - admin, manager, or viewer
- `can_manage_kg` - Access to KG market
- `can_manage_us` - Access to US market
- `can_view_orders` - View orders permission
- `can_edit_orders` - Edit orders permission
- `can_cancel_orders` - Cancel orders permission
- `can_view_revenue` - View revenue permission
- `can_export_data` - Export data permission
- `is_active` - Manager status
- `last_login` - Last login timestamp

**Methods:**

- `accessible_markets` - Returns list of accessible markets

**Use Case:**

```python
# Create a store manager
manager = StoreManager.objects.create(
    user=user,
    role='manager',
    can_manage_kg=True,
    can_manage_us=False,
    can_view_orders=True,
    can_edit_orders=True,
)

# Check accessible markets
markets = manager.accessible_markets  # ['KG']
```

---

### ManagerSettings Model

Manager preferences and UI settings.

**Fields:**

- `manager` - OneToOne with StoreManager
- `language` - ru, ky, or en
- `theme` - light, dark, or system
- `active_market` - Currently selected market (KG/US)
- `notify_new_orders` - Notification toggle
- `notify_status_changes` - Notification toggle
- `notify_daily_report` - Notification toggle
- `notify_delivery_errors` - Notification toggle
- `report_email` - Email for daily reports
- `default_order_filter` - Default filter on dashboard
- `orders_per_page` - Pagination setting

**Use Case:**

```python
# Get manager settings
settings = manager.settings

# Update language
settings.language = 'en'
settings.save()

# Enable notifications
settings.notify_new_orders = True
settings.notify_daily_report = True
settings.report_email = 'manager@example.com'
settings.save()
```

---

### RevenueSnapshot Model

Store revenue metrics for analytics.

**Fields:**

- `market` - KG or US
- `snapshot_type` - hourly, daily, weekly, monthly
- `snapshot_date` - Date of snapshot
- `snapshot_hour` - Hour (0-23) for hourly snapshots
- `total_revenue` - Total revenue amount
- `currency` / `currency_code` - Currency info
- `total_orders` - Number of orders
- `completed_orders` - Completed count
- `cancelled_orders` - Cancelled count
- `pending_orders` - Pending count
- `average_order_value` - Average order amount
- `revenue_change_percent` - % change from previous period
- `orders_change_percent` - % change from previous period

**Use Case:**

```python
from store_manager.utils import create_or_update_revenue_snapshot

# Create today's snapshot
snapshot = create_or_update_revenue_snapshot(
    market='KG',
    snapshot_type='daily'
)

# Get hourly breakdown
hourly_revenue = get_hourly_revenue(market='KG')
```

---

### ManagerActivityLog Model

Audit trail for all manager actions.

**Fields:**

- `manager` - ForeignKey to StoreManager
- `action_type` - Type of action (view_order, update_status, etc.)
- `order` - Related order (optional)
- `market` - Market where action occurred
- `description` - Action description
- `old_value` / `new_value` - For updates
- `ip_address` - Manager's IP
- `user_agent` - Browser info
- `created_at` - Timestamp

**Action Types:**

- `view_order` - Viewed Order
- `update_status` - Updated Order Status
- `cancel_order` - Cancelled Order
- `resume_order` - Resumed Order
- `export_data` - Exported Data
- `view_revenue` - Viewed Revenue
- `switch_market` - Switched Market
- `login` - Logged In
- `logout` - Logged Out

**Use Case:**

```python
from store_manager.utils import log_manager_activity

# Log status change
log_manager_activity(
    manager=manager,
    action_type='update_status',
    order=order,
    market='KG',
    description='Changed order status',
    old_value='pending',
    new_value='shipped',
    ip_address='192.168.1.1',
    user_agent='Mozilla/5.0...'
)
```

---

### ManagerNotification Model

In-app notifications for managers.

**Fields:**

- `manager` - ForeignKey to StoreManager
- `notification_type` - new_order, status_change, delivery_error, system
- `priority` - low, medium, high, urgent
- `title` - Notification title
- `message` - Notification message
- `order` - Related order (optional)
- `market` - Related market
- `is_read` - Read status
- `read_at` - Read timestamp
- `action_url` - URL for action button

**Use Case:**

```python
from store_manager.utils import notify_manager

# Notify manager of new order
notify_manager(
    manager=manager,
    notification_type='new_order',
    title='Новый заказ #1024',
    message='Новый заказ на сумму 1250 сом',
    order=order,
    market='KG',
    priority='high',
    action_url='/admin/orders/1024'
)
```

---

### DailyReport Model

Automated daily reports for managers.

**Fields:**

- `manager` - ForeignKey to StoreManager
- `market` - Report market
- `report_date` - Date of report
- `status` - pending, generated, sent, failed
- `report_data` - JSON with revenue/order data
- `sent_to_email` - Email address
- `sent_at` - Sent timestamp
- `error_message` - Error if failed
- `retry_count` - Number of retry attempts

**Use Case:**

```python
# Generate daily report
report = DailyReport.objects.create(
    manager=manager,
    market='KG',
    report_date=today,
    report_data={
        'revenue': 7150,
        'orders': 5,
        'average': 1430,
    },
    status='generated'
)

# Send report via email
# (Implement email sending logic)
report.sent_to_email = manager.settings.report_email
report.sent_at = timezone.now()
report.status = 'sent'
report.save()
```

---

## 🔧 Utility Functions

### Revenue Tracking

```python
from store_manager.utils import (
    calculate_revenue_snapshot,
    create_or_update_revenue_snapshot,
    get_today_revenue,
    get_hourly_revenue
)

# Calculate revenue for today
metrics = calculate_revenue_snapshot(market='KG')
# Returns: {total_revenue, total_orders, completed_orders, etc.}

# Create/update snapshot
snapshot = create_or_update_revenue_snapshot(
    market='KG',
    snapshot_type='daily'
)

# Get today's revenue summary
today_data = get_today_revenue(market='KG')
# Returns: {total_revenue, revenue_change, total_orders, etc.}

# Get hourly breakdown
hourly = get_hourly_revenue(market='KG')
# Returns: [{time: '09:00', amount: '3100 KGS', is_highlighted: True}, ...]
```

### Order Management

```python
from store_manager.utils import (
    get_active_orders_count,
    get_today_orders,
    get_recent_orders,
    filter_orders_by_status
)

# Get active orders count
count = get_active_orders_count(market='KG')

# Get today's orders
orders = get_today_orders(market='KG')

# Get recent orders
recent = get_recent_orders(market='KG', limit=10)

# Filter orders by status
orders = Order.objects.filter(user__market='KG')
filtered = filter_orders_by_status(orders, 'В пути')
```

### Activity Logging

```python
from store_manager.utils import log_manager_activity

# Log manager action
log = log_manager_activity(
    manager=manager,
    action_type='update_status',
    order=order,
    market='KG',
    description='Changed status from pending to shipped',
    old_value='pending',
    new_value='shipped',
    ip_address=request.META.get('REMOTE_ADDR'),
    user_agent=request.META.get('HTTP_USER_AGENT')
)
```

### Notifications

```python
from store_manager.utils import notify_manager

# Send notification
notification = notify_manager(
    manager=manager,
    notification_type='new_order',
    title='Новый заказ',
    message='Поступил новый заказ #1024',
    order=order,
    market='KG',
    priority='high',
    action_url='/orders/1024'
)
```

---

## 🚀 API Endpoints (To Be Implemented)

### Authentication

```
POST   /api/v1/manager/auth/login          - Manager login
POST   /api/v1/manager/auth/logout         - Manager logout
GET    /api/v1/manager/auth/profile        - Get manager profile
```

### Dashboard

```
GET    /api/v1/manager/dashboard           - Dashboard summary
GET    /api/v1/manager/dashboard/stats     - Statistics
```

### Orders

```
GET    /api/v1/manager/orders              - List orders (filtered by market)
GET    /api/v1/manager/orders/today        - Today's orders
GET    /api/v1/manager/orders/{id}         - Order detail
PATCH  /api/v1/manager/orders/{id}/status  - Update order status
POST   /api/v1/manager/orders/{id}/cancel  - Cancel order
POST   /api/v1/manager/orders/{id}/resume  - Resume order
GET    /api/v1/manager/orders/search       - Search orders
```

### Revenue

```
GET    /api/v1/manager/revenue/today       - Today's revenue
GET    /api/v1/manager/revenue/hourly      - Hourly breakdown
GET    /api/v1/manager/revenue/daily       - Daily data
GET    /api/v1/manager/revenue/monthly     - Monthly data
```

### Settings

```
GET    /api/v1/manager/settings            - Get settings
PUT    /api/v1/manager/settings            - Update settings
POST   /api/v1/manager/market/switch       - Switch market
```

### Notifications

```
GET    /api/v1/manager/notifications       - List notifications
GET    /api/v1/manager/notifications/unread - Unread count
PATCH  /api/v1/manager/notifications/{id}/read - Mark as read
POST   /api/v1/manager/notifications/read-all  - Mark all as read
```

### Activity Logs

```
GET    /api/v1/manager/activity-logs       - My activity logs
GET    /api/v1/manager/activity-logs/export - Export logs
```

---

## 📱 Frontend Integration

### Market Switcher Component

The frontend uses `MarketIndicator` component to:

- Show current market (KG DB or US DB)
- Display connection status
- Allow switching between markets
- Update all data when market changes

**Example:**

```tsx
<MarketIndicator
  currentMarket={currentMarket}
  onMarketChange={handleMarketChange}
  showSwitcher={true}
/>
```

### Dashboard Views

**Main Views:**

1. **Dashboard** - Overview with cards for orders, revenue
2. **Orders** - Today's orders list
3. **All Orders** - Complete order history
4. **Order Detail** - Individual order view
5. **Revenue** - Revenue analytics
6. **Settings** - Manager preferences

---

## 🔐 Permission System

### Manager Roles

| Role        | Description      | Permissions                    |
| ----------- | ---------------- | ------------------------------ |
| **Admin**   | Full access      | All permissions                |
| **Manager** | Standard manager | View/edit orders, view revenue |
| **Viewer**  | Read-only access | View orders only               |

### Granular Permissions

- `can_view_orders` - View order list and details
- `can_edit_orders` - Change order status
- `can_cancel_orders` - Cancel/resume orders
- `can_view_revenue` - Access revenue analytics
- `can_export_data` - Export data to CSV/Excel

### Market Access

- `can_manage_kg` - Access Kyrgyzstan market
- `can_manage_us` - Access United States market

---

## 📊 Revenue Snapshot System

### Automatic Snapshots

Create a scheduled task (using Celery or Django-Q) to:

```python
from store_manager.utils import create_or_update_revenue_snapshot

# Hourly task
@scheduled_task('cron', hour='*', minute=0)
def create_hourly_snapshots():
    for market in ['KG', 'US']:
        create_or_update_revenue_snapshot(
            market=market,
            snapshot_type='hourly',
            snapshot_hour=timezone.now().hour
        )

# Daily task
@scheduled_task('cron', hour=23, minute=59)
def create_daily_snapshots():
    for market in ['KG', 'US']:
        create_or_update_revenue_snapshot(
            market=market,
            snapshot_type='daily'
        )
```

---

## 🔔 Notification System

### Trigger Notifications

```python
# When new order is created
from store_manager.utils import notify_manager

# Get all managers for this market
managers = StoreManager.objects.filter(
    can_manage_kg=True,  # or can_manage_us
    is_active=True
)

for manager in managers:
    notify_manager(
        manager=manager,
        notification_type='new_order',
        title='Новый заказ',
        message=f'Новый заказ #{order.order_number} на сумму {order.total_amount}',
        order=order,
        market='KG',
        priority='high'
    )
```

---

## 🧪 Testing

### Test Manager Creation

```python
from users.models import User
from store_manager.models import StoreManager, ManagerSettings

# Create manager user
user = User.objects.create(
    phone='+996700123456',
    full_name='Азамат Токтосунов',
    market='KG',
    is_staff=True
)

# Create manager profile
manager = StoreManager.objects.create(
    user=user,
    role='manager',
    can_manage_kg=True,
    can_manage_us=False
)

# Create settings
settings = ManagerSettings.objects.create(
    manager=manager,
    language='ru',
    notify_new_orders=True
)
```

---

## 📋 Next Steps

- [ ] Implement REST API endpoints
- [ ] Add JWT authentication for managers
- [ ] Create automated revenue snapshot tasks
- [ ] Implement email reporting system
- [ ] Add data export functionality (CSV/Excel)
- [ ] Create manager dashboard analytics
- [ ] Add push notifications (FCM/OneSignal)
- [ ] Implement real-time updates (WebSocket)

---

**Built for MARQUE Multi-Market Fashion Platform** 🛍️
