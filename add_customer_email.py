import os
import django
from django.db import connection

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventory.settings')
django.setup()

sql = "ALTER TABLE customers ADD COLUMN email VARCHAR(100);"

try:
    with connection.cursor() as cursor:
        print(f"Executing: {sql}")
        cursor.execute(sql)
    print("Schema update completed: Added email to customers.")
except Exception as e:
    if "Duplicate column name" in str(e):
        print("Column 'email' already exists in 'customers'.")
    else:
        print(f"Error: {e}")
