import os
import django
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventory.settings')
django.setup()

from inventory import models

def test_fetch():
    print("Testing PO Item Verification...")
    
    # 1. Create a PO
    po = models.PurchaseOrders.objects.create(
        supplier_id=1, # Assuming supplier 1 exists, or we create one. 
        # Using a dummy ID might fail if constraint exists, but here constraints seem loose or verified by app logic.
        # Safest to create a supplier
        po_date=date.today(),
        status='pending'
    )
    print(f"Created PO: {po.id}")
    
    # 2. Add Items
    # Need a product
    cat = models.Categories.objects.create(cat_name="Test Cat", created_at=date.today())
    prod = models.Products.objects.create(cat_id=cat.id, product_name="Test Product", price=100, created_at=date.today())
    
    item = models.PurchaseOrderItems.objects.create(
        po=po,
        product=prod,
        quantity=5,
        unit_price=100,
        total_price=500
    )
    print(f"Created Item: {item.id} linked to PO {item.po_id}")
    
    # 3. Simulate View Logic
    # sdata = models.PurchaseOrders.objects.get(id=poid)
    # items = models.PurchaseOrderItems.objects.filter(po=sdata)
    
    fetched_po = models.PurchaseOrders.objects.get(id=po.id)
    fetched_items = models.PurchaseOrderItems.objects.filter(po=fetched_po)
    
    print(f"Fetched Items Count: {len(fetched_items)}")
    
    for i in fetched_items:
        print(f"Item ID: {i.id}, Product: {i.product.product_name}, Qty: {i.quantity}")
        
    if len(fetched_items) > 0:
        print("PASS: Items fetched successfully.")
    else:
        print("FAIL: No items fetched.")
        
    # Cleanup
    item.delete()
    po.delete()
    prod.delete()
    cat.delete()

if __name__ == "__main__":
    test_fetch()
