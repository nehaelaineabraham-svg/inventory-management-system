import os
import django
from django.db import connection

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventory.settings')
django.setup()

sql_commands = [
    "ALTER TABLE products ADD COLUMN reorder_level INTEGER DEFAULT 10;",
    "ALTER TABLE grn ADD COLUMN batch_no VARCHAR(50);",
    "ALTER TABLE grn ADD COLUMN expiry_date DATE;",
    "ALTER TABLE grn ADD COLUMN location VARCHAR(100);",
    "ALTER TABLE stock_ledger ADD COLUMN batch_no VARCHAR(50);",
    "ALTER TABLE stock_ledger ADD COLUMN expiry_date DATE;",
    "ALTER TABLE stock_ledger ADD COLUMN location VARCHAR(100);"
]

try:
    with connection.cursor() as cursor:
        for sql in sql_commands:
            try:
                print(f"Executing: {sql}")
                cursor.execute(sql)
            except Exception as e:
                # Ignore if column exists error (MySQL error 1060)
                if "Duplicate column name" in str(e):
                    print(f"Skipping (already exists): {sql}")
                else:
                    print(f"Error executing {sql}: {e}")
    print("Schema update completed.")
except Exception as e:
    print(f"Connection Error: {e}")
