# ⏰ Cron Job Setup for Exchange Rate Updates

This guide shows how to set up automatic daily exchange rate updates using cron jobs.

## 📋 Options

### Option 1: Traditional Linux/Mac Cron (Local Server)

#### Step 1: Create the Script

A script is already created at `scripts/update_exchange_rates.sh`. Make sure it's executable:

```bash
chmod +x scripts/update_exchange_rates.sh
```

#### Step 2: Test the Script

Test the script manually first:

```bash
./scripts/update_exchange_rates.sh
```

#### Step 3: Set Up Cron Job

Edit your crontab:

```bash
crontab -e
```

Add one of these lines (choose based on when you want updates):

```bash
# Update exchange rates daily at 2:00 AM
0 2 * * * cd /Users/macbookpro/M4_Projects/Prodaction/marque_backend_with_drangorestframework && /path/to/python manage.py update_exchange_rates >> /var/log/exchange_rates.log 2>&1

# Or use the script (recommended)
0 2 * * * /Users/macbookpro/M4_Projects/Prodaction/marque_backend_with_drangorestframework/scripts/update_exchange_rates.sh >> /var/log/exchange_rates.log 2>&1

# Update twice daily (morning and evening)
0 2,14 * * * /Users/macbookpro/M4_Projects/Prodaction/marque_backend_with_drangorestframework/scripts/update_exchange_rates.sh >> /var/log/exchange_rates.log 2>&1
```

**Cron Format:**

```
* * * * *
│ │ │ │ │
│ │ │ │ └─── Day of week (0-7, Sunday = 0 or 7)
│ │ │ └───── Month (1-12)
│ │ └─────── Day of month (1-31)
│ └───────── Hour (0-23)
└─────────── Minute (0-59)
```

#### Step 4: Verify Cron Job

Check if your cron job is set up:

```bash
crontab -l
```

#### Step 5: Check Logs

Monitor the log file to ensure it's working:

```bash
tail -f /var/log/exchange_rates.log
```

---

### Option 2: Railway (Recommended for Production)

Railway supports cron jobs through their platform.

#### Step 1: Create `railway.json`

Create a file `railway.json` in your project root:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "gunicorn main.wsgi:application",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  },
  "crons": [
    {
      "command": "python manage.py update_exchange_rates",
      "schedule": "0 2 * * *",
      "timezone": "UTC"
    }
  ]
}
```

#### Step 2: Deploy

Railway will automatically detect and set up the cron job when you deploy.

**Note:** Railway cron jobs run in UTC time. Adjust the schedule accordingly:

- `0 2 * * *` = 2:00 AM UTC daily
- `0 6 * * *` = 6:00 AM UTC daily (adjust for your timezone)

---

### Option 3: Heroku Scheduler

If you're using Heroku:

#### Step 1: Install Heroku Scheduler Addon

```bash
heroku addons:create scheduler:standard
```

#### Step 2: Configure Scheduled Job

1. Go to your Heroku dashboard
2. Click on "Heroku Scheduler"
3. Click "Create job"
4. Set:
   - **Schedule:** `0 2 * * *` (daily at 2 AM)
   - **Run Command:** `python manage.py update_exchange_rates`
   - **Dyno Size:** Standard-1X (or your preference)

---

### Option 4: Docker with Cron

If you're using Docker:

#### Step 1: Create `Dockerfile.cron`

```dockerfile
FROM your-django-image:latest

# Install cron
RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

# Copy cron file
COPY crontab /etc/cron.d/exchange-rates-cron

# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/exchange-rates-cron

# Apply cron job
RUN crontab /etc/cron.d/exchange-rates-cron

# Create the log file to be able to run tail
RUN touch /var/log/exchange_rates.log

# Run the command on container startup
CMD cron && tail -f /var/log/exchange_rates.log
```

#### Step 2: Create `crontab` file

```bash
# Update exchange rates daily at 2 AM
0 2 * * * cd /app && python manage.py update_exchange_rates >> /var/log/exchange_rates.log 2>&1
```

---

### Option 5: Python APScheduler (In-App Scheduling)

If you want to run the scheduler within your Django app:

#### Step 1: Install APScheduler

```bash
pip install apscheduler
```

Add to `requirements.txt`:

```
apscheduler==3.10.4
```

#### Step 2: Create `products/scheduler.py`

```python
from apscheduler.schedulers.background import BackgroundScheduler
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)

def start_scheduler():
    scheduler = BackgroundScheduler()

    # Schedule exchange rate updates daily at 2 AM
    scheduler.add_job(
        update_exchange_rates,
        'cron',
        hour=2,
        minute=0,
        id='update_exchange_rates',
        replace_existing=True
    )

    scheduler.start()
    logger.info("Scheduler started")

def update_exchange_rates():
    """Update exchange rates from API"""
    try:
        call_command('update_exchange_rates')
        logger.info("Exchange rates updated successfully")
    except Exception as e:
        logger.error(f"Failed to update exchange rates: {str(e)}")
```

#### Step 3: Add to `main/__init__.py` or `products/apps.py`

```python
# In products/apps.py
from django.apps import AppConfig

class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'products'

    def ready(self):
        if not os.environ.get('RUN_MAIN'):
            return
        from .scheduler import start_scheduler
        start_scheduler()
```

---

## 🔍 Monitoring & Troubleshooting

### Check if Cron is Running

```bash
# Check cron service status
sudo systemctl status cron  # Linux
sudo service cron status     # Some Linux distros

# Check cron logs
grep CRON /var/log/syslog   # Linux
grep cron /var/log/system.log  # Mac
```

### Test Cron Job Manually

```bash
# Run the command directly
python manage.py update_exchange_rates

# Or test the script
./scripts/update_exchange_rates.sh
```

### Common Issues

1. **Cron job not running:**

   - Check cron service is running
   - Verify file paths are absolute
   - Check permissions on script
   - Review cron logs

2. **Python not found:**

   - Use full path to Python: `/usr/bin/python3` or `/path/to/venv/bin/python`
   - Or activate virtual environment in script

3. **Django settings not found:**

   - Ensure `DJANGO_SETTINGS_MODULE` is set
   - Or run from project root directory

4. **Permission denied:**
   - Make script executable: `chmod +x script.sh`
   - Check file ownership

---

## 📊 Recommended Schedule

- **Daily at 2 AM**: Good for most use cases (rates don't change frequently)
- **Twice daily (2 AM & 2 PM)**: For more frequent updates
- **Every 6 hours**: For high-frequency trading (not recommended for e-commerce)

**Note:** Exchange rates typically update once per day, so daily updates are usually sufficient.

---

## 🎯 Quick Setup (Railway - Recommended)

If you're using Railway, simply create `railway.json`:

```json
{
  "crons": [
    {
      "command": "python manage.py update_exchange_rates",
      "schedule": "0 2 * * *",
      "timezone": "UTC"
    }
  ]
}
```

Deploy and Railway will handle the rest!

---

## 📝 Notes

- All times are in UTC unless specified
- Logs are important for debugging - always redirect output to a log file
- Test manually before setting up automatic updates
- Monitor the first few runs to ensure everything works correctly
