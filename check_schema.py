import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventory.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()

# Get actual column names from database
tables = {
    'users': [],
    'categories': [],
    'products': [],
    'suppliers': []
}

for table in tables.keys():
    cursor.execute(f"SHOW COLUMNS FROM {table}")
    columns = cursor.fetchall()
    print(f"\n{table.upper()} TABLE:")
    print("-" * 60)
    for col in columns:
        field_name = col[0]
        field_type = col[1]
        print(f"  {field_name:<30} {field_type}")
        tables[table].append(field_name)

print("\n\nSUMMARY:")
print("="*60)
for table, cols in tables.items():
    print(f"{table}: {', '.join(cols)}")
