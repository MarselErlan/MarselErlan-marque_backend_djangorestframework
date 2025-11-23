# 💱 Automatic Exchange Rate Updates

This guide explains how to set up automatic exchange rate updates from external APIs instead of manually entering rates in the Django admin.

## 📋 Overview

The system supports fetching exchange rates from multiple API providers:

- **exchangerate-api.com** (Free tier: 1500 requests/month, **No API key required**)
- **fixer.io** (Free tier: 100 requests/month, requires API key)
- **currencyapi.net** (Free tier: 300 requests/month, requires API key)

## 🚀 Quick Start

### 1. Install Dependencies

The `requests` library is already added to `requirements.txt`. Install it:

```bash
pip install -r requirements.txt
```

### 2. Update Exchange Rates (Command Line)

Run the management command to update exchange rates:

```bash
# Using exchangerate-api.com (no API key needed)
python manage.py update_exchange_rates

# Using a specific API provider
python manage.py update_exchange_rates --api exchangerate
python manage.py update_exchange_rates --api fixer
python manage.py update_exchange_rates --api currencyapi

# Force update even if rates were recently updated
python manage.py update_exchange_rates --force
```

### 3. Update Exchange Rates (API Endpoint)

You can also trigger updates via API (requires admin authentication):

```bash
# POST request to update rates
curl -X POST "https://your-domain.com/api/v1/currencies/update-rates/?api=exchangerate" \
  -H "Authorization: Token YOUR_ADMIN_TOKEN"

# With force flag
curl -X POST "https://your-domain.com/api/v1/currencies/update-rates/?api=exchangerate&force=true" \
  -H "Authorization: Token YOUR_ADMIN_TOKEN"
```

## 🔑 API Key Setup (Optional)

### For Fixer.io

1. Sign up at https://fixer.io/
2. Get your API key
3. Add to `.env` file:

```env
FIXER_API_KEY=your_fixer_api_key_here
```

### For CurrencyAPI.net

1. Sign up at https://currencyapi.net/
2. Get your API key
3. Add to `.env` file:

```env
CURRENCYAPI_KEY=your_currencyapi_key_here
```

**Note:** exchangerate-api.com doesn't require an API key for basic usage.

## ⏰ Automatic Updates (Cron Job)

Set up a cron job to automatically update exchange rates daily:

### Linux/Mac (crontab)

```bash
# Edit crontab
crontab -e

# Add this line to update rates daily at 2 AM
0 2 * * * cd /path/to/your/project && /path/to/python manage.py update_exchange_rates >> /var/log/exchange_rates.log 2>&1
```

### Using Django Management Command in Production

If you're using Railway, Heroku, or similar platforms, you can set up a scheduled task:

1. **Railway**: Use Railway's Cron Jobs feature
2. **Heroku**: Use Heroku Scheduler addon
3. **Docker**: Add to your docker-compose.yml or use a separate cron container

### Example: Railway Cron Job

In your Railway project, add a cron job:

```json
{
  "cron": "0 2 * * *",
  "command": "python manage.py update_exchange_rates"
}
```

## 📊 How It Works

1. **Fetches Rates**: The command queries the selected API for current exchange rates
2. **Converts Format**: Rates are normalized to match your database format (1 USD = X KGS)
3. **Updates Database**: Only active currencies are updated
4. **Rate Limiting**: By default, rates are not updated if they were updated within the last hour (unless `--force` is used)

## 🔍 Rate Limiting

- **exchangerate-api.com**: 1500 requests/month (free tier)
- **fixer.io**: 100 requests/month (free tier)
- **currencyapi.net**: 300 requests/month (free tier)

The system automatically skips updates if rates were updated within the last hour to prevent unnecessary API calls.

## 🛠️ Troubleshooting

### Error: "API request failed"

- Check your internet connection
- Verify API key (if using fixer.io or currencyapi.net)
- Check if you've exceeded API rate limits

### Error: "Currency not found in database"

- Make sure currencies are created in Django admin first
- Only active currencies will be updated

### Rates Not Updating

- Check if rates were recently updated (within last hour)
- Use `--force` flag to override the time check
- Check API response in command output

## 📝 Example Output

```
Fetching exchange rates from exchangerate API...
Updated KGS: 89.000000 -> 89.500000
Successfully updated 1 currency exchange rate(s)
```

## 🔐 Security

- The API endpoint (`/currencies/update-rates/`) requires admin authentication
- Only users with `IsAdminUser` permission can trigger updates via API
- Command line usage requires server access

## 📚 API Documentation

The endpoint is documented in your API schema at:

- `/api/schema/swagger-ui/` (Swagger UI)
- `/api/schema/redoc/` (ReDoc)

## 🎯 Best Practices

1. **Schedule Daily Updates**: Set up a cron job to update rates once per day (rates don't change that frequently)
2. **Monitor API Usage**: Keep track of your API usage to avoid hitting rate limits
3. **Use exchangerate-api.com**: Recommended for free tier (no API key, highest rate limit)
4. **Backup Rates**: Keep manual backups of important exchange rates
5. **Test First**: Test the command manually before setting up automatic updates

## 🆘 Support

If you encounter issues:

1. Check the command output for error messages
2. Verify your API keys are set correctly
3. Ensure currencies exist in the database
4. Check API provider status pages
