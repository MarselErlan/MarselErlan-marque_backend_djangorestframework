#!/bin/bash
# Production Migration Script for Store Manager
# Run this on your production server (Railway)

echo "=========================================="
echo "Running Store Manager Migration"
echo "=========================================="

# Check migration status first
echo ""
echo "📋 Checking migration status..."
python manage.py showmigrations store_manager

echo ""
echo "🚀 Running migration..."
python manage.py migrate store_manager

echo ""
echo "✅ Verifying migration..."
python manage.py showmigrations store_manager

echo ""
echo "🔍 Running system check..."
python manage.py check

echo ""
echo "=========================================="
echo "Migration Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Refresh your Django Admin page"
echo "2. The ProgrammingError should be fixed"
echo "3. StoreManager admin should show 'store' field"
echo ""

