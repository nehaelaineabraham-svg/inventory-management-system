import os
import django
from django.test import Client, RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventory.settings')
django.setup()

from inventory import models
from admin.views import update_purchase_order
import datetime

def setup_test_data():
    # Create Supplier
    sup, _ = models.Suppliers.objects.get_or_create(
        supplier_name="Test Supplier",
        email="test@example.com",
        created_at=datetime.datetime.now()
    )
    
    # Create Product
    prod, _ = models.Products.objects.get_or_create(
        product_name="Test Product",
        price=10.00,
        created_at=datetime.datetime.now()
    )
    
    # Create PO
    po = models.PurchaseOrders.objects.create(
        supplier_id=sup.id,
        po_date=datetime.date.today(),
        status='pending'
    )
    
    # Create Item
    models.PurchaseOrderItems.objects.create(
        po=po,
        product=prod,
        quantity=5,
        unit_price=10.00,
        total_price=50.00
    )
    
    return po, sup, prod

def test_update_po():
    print("Setting up test data...")
    po, sup, prod = setup_test_data()
    print(f"Created PO {po.id} with status '{po.status}' and 1 item.")
    
    # Prepare Mock Post Data
    # Simulating changing status to 'received', changing qty to 10
    post_data = {
        'poid': po.id,
        'supplier_id': sup.id,
        'po_date': datetime.date.today().strftime('%Y-%m-%d'),
        'status': 'received',
        'product_id[]': [prod.id],
        'quantity[]': [10],
        'price[]': [10.00]
    }
    
    print("\nSimulating POST request to update PO...")
    factory = RequestFactory()
    request = factory.post('/admin/update_purchase_order/', post_data)
    
    # Add session and messages support
    middleware = SessionMiddleware(lambda x: None)
    middleware.process_request(request)
    request.session.save()
    
    messages = MessageMiddleware(lambda x: None)
    messages.process_request(request)
    
    # Call the view
    response = update_purchase_order(request)
    
    # Verify PO Update
    updated_po = models.PurchaseOrders.objects.get(id=po.id)
    print(f"Updated PO Status: {updated_po.status}")
    
    if updated_po.status == 'received':
        print("PASS: Status updated correctly.")
    else:
        print(f"FAIL: Expected status 'received', got '{updated_po.status}'")
        
    # Verify Items Update
    items = models.PurchaseOrderItems.objects.filter(po=updated_po)
    print(f"Updated Item Count: {items.count()}")
    
    if items.count() == 1:
        item = items.first()
        print(f"Item Qty: {item.quantity}, Total: {item.total_price}")
        if item.quantity == 10 and item.total_price == 100.00:
            print("PASS: Item quantity and total updated correctly.")
        else:
            print("FAIL: Item details incorrect.")
    else:
        print("FAIL: Item count incorrect.")

if __name__ == '__main__':
    try:
        test_update_po()
    except Exception as e:
        print(f"An error occurred: {e}")
