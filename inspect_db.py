import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventory.settings')
django.setup()

from django.core.management import call_command
from io import StringIO

# Capture inspectdb output
output = StringIO()
call_command('inspectdb', 'users', 'categories', 'products', 'suppliers', stdout=output)

# Write to file
with open('inspected_models.txt', 'w', encoding='utf-8') as f:
    f.write(output.getvalue())

print("Models written to inspected_models.txt")
print("\n" + "="*60)
print(output.getvalue())
