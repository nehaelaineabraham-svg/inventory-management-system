import os
import django
import sys

# Setup Django environment
sys.path.append(r'c:\Users\Neha\Desktop\inventory sir with style')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventory.settings') 
django.setup()

from inventory import models
from django.db.models import Q

def verify_active_users():
    total_users_count = models.Users.objects.count()
    active_users_count = models.Users.objects.filter(status=1).count()
    inactive_users_count = models.Users.objects.filter(Q(status=0) | Q(status__isnull=True)).count()
    
    print(f"Total Users: {total_users_count}")
    print(f"Active Users (status=1): {active_users_count}")
    print(f"Inactive Users: {inactive_users_count}")
    
    if total_users_count == (active_users_count + inactive_users_count):
        print("Verification successful: Active + Inactive = Total")
    else:
        print("Note: Some users might have other status values.")

if __name__ == "__main__":
    try:
        verify_active_users()
    except Exception as e:
        print(f"Error during verification: {e}")
