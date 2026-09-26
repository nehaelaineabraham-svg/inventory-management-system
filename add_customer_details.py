import os
import django
from django.db import connection

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventory.settings')
django.setup()

sql_statements = [
    "ALTER TABLE customers ADD COLUMN place VARCHAR(100);",
    "ALTER TABLE customers ADD COLUMN address TEXT;"
]

try:
    with connection.cursor() as cursor:
        for sql in sql_statements:
            try:
                print(f"Executing: {sql}")
                cursor.execute(sql)
                print("Success.")
            except Exception as e:
                print(f"Error executing {sql}: {e}")
                
    print("Schema update completed.")
except Exception as e:
    print(f"Connection Error: {e}")
