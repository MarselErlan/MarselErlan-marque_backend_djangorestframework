#!/usr/bin/env python
"""
Quick script to check the actual table name for Product model
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main.settings')
django.setup()

from products.models import Product
from django.db import connection

print(f"Product model db_table: {Product._meta.db_table}")
print(f"Product model table name: {Product._meta.db_table}")

# Check what tables actually exist
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name LIKE '%product%'
        ORDER BY table_name
    """)
    tables = cursor.fetchall()
    print("\nTables with 'product' in name:")
    for table in tables:
        print(f"  - {table[0]}")
    
    # Check products table columns
    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'products'
        ORDER BY ordinal_position
    """)
    columns = cursor.fetchall()
    print("\nColumns in 'products' table:")
    for col_name, col_type in columns:
        print(f"  - {col_name}: {col_type}")

