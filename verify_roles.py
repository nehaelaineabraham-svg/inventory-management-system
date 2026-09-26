import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventory.settings')
django.setup()

from inventory.models import Users, Login

def verify():
    print("Testing Role Creation and Login Sync...")
    
    test_email = "test_manager@example.com"
    test_role = "manager"
    
    # Cleanup existing
    Users.objects.filter(email=test_email).delete()
    Login.objects.filter(user_name=test_email).delete()
    
    # Create User (simulating save_user logic)
    user = Users(
        name="Test Manager",
        email=test_email,
        role=test_role,
        password="password123",
        status=1
    )
    user.save()
    
    # Create Login
    log = Login(
        user_name=test_email,
        password="password123",
        user_type=test_role,
        user_status='active'
    )
    log.save()
    
    # Verify
    u = Users.objects.filter(email=test_email).first()
    l = Login.objects.filter(user_name=test_email).first()
    
    if u and u.role == test_role:
        print(f"SUCCESS: User created with role {u.role}")
    else:
        print("FAILURE: User role mismatch or not created")
        
    if l and l.user_type == test_role:
        print(f"SUCCESS: Login created with user_type {l.user_type}")
    else:
        print("FAILURE: Login user_type mismatch or not created")
        
    # Cleanup
    # u.delete()
    # l.delete()

if __name__ == "__main__":
    verify()
