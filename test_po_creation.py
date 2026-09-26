import os
import django
from django.test import Client
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventory.settings')
django.setup()

from inventory import models

def test_po_create():
    print("Testing PO Creation via POST...")
    
    # Setup data
    s = models.Suppliers.objects.first()
    if not s:
        s = models.Suppliers.objects.create(supplier_name="Test Supplier", created_at=date.today())
        
    p = models.Products.objects.first()
    if not p:
        cat = models.Categories.objects.create(cat_name="Test Cat", created_at=date.today())
        p = models.Products.objects.create(cat_id=cat.id, product_name="Test P", price=100, created_at=date.today())
        
    c = Client()
    
    # POST Data
    post_data = {
        'supplier_id': s.id,
        'po_date': '2026-02-18',
        'status': 'pending',
        'product_id[]': [p.id],
        'quantity[]': [10],
        'price[]': [100.00]
    }
    
    print(f"Posting data: {post_data}")
    
    response = c.post('/administrator/save_purchase_order/', post_data)
    
    print(f"Response Status: {response.status_code}")
    
    if response.status_code == 302:
        print("Redirected successfully.")
    else:
        print(f"Failed. Content: {response.content}")
        
    # Check last PO
    last_po = models.PurchaseOrders.objects.last()
    print(f"Last PO ID: {last_po.id}")
    
    items_count = models.PurchaseOrderItems.objects.filter(po_id=last_po.id).count()
    print(f"Items Count: {items_count}")
    
    if items_count == 1:
        print("PASS: Item saved correctly.")
    else:
        print("FAIL: Item not saved.")

if __name__ == "__main__":
    test_po_create()
