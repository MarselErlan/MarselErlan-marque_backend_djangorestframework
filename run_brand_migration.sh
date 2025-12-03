#!/bin/bash

# Brand Migration Script
# This script will rollback and re-run the brand migration

cd /Users/macbookpro/M4_Projects/Prodaction/marque_backend_with_drangorestframework

echo "🔄 Step 1: Rolling back to migration 0006..."
python manage.py migrate products 0006

echo ""
echo "✅ Rollback complete!"
echo ""
echo "🚀 Step 2: Running brand migration..."
python manage.py migrate products

echo ""
echo "✅ Migration complete!"
echo ""
echo "📋 Step 3: Verifying migration status..."
python manage.py showmigrations products | tail -5

echo ""
echo "✨ Done! Check the output above for any errors."

