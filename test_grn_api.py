import os
import django
import json
from django.test import Client

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventory.settings')
django.setup()

from inventory import models
from datetime import date

def test_api():
    print("Setting up test data...")
    # Create Supplier, Categories, Products
    supplier = models.Suppliers.objects.create(
        supplier_name="Test Supplier API", 
        created_at=date.today()
    )
    
    cat = models.Categories.objects.create(
        cat_name="API Cat",
        status=1,
        created_at=date.today()
    )
    
    p1 = models.Products.objects.create(
        cat_id=cat.id, product_name="API Prod 1", unit="kg", price=100, created_at=date.today()
    )
    p2 = models.Products.objects.create(
        cat_id=cat.id, product_name="API Prod 2", unit="kg", price=200, created_at=date.today()
    )
    p3 = models.Products.objects.create(
        cat_id=cat.id, product_name="Other Prod", unit="kg", price=300, created_at=date.today()
    )
    
    # Create PO with p1 and p2 only
    po = models.PurchaseOrders.objects.create(
        supplier_id=supplier.id, po_date=date.today(), status='pending'
    )
    
    models.PurchaseOrderItems.objects.create(
        po=po, product=p1, quantity=10, unit_price=100, total_price=1000
    )
    models.PurchaseOrderItems.objects.create(
        po=po, product=p2, quantity=5, unit_price=200, total_price=1000
    )
    
    print(f"Created PO {po.id} with Products {p1.id}, {p2.id}")
    
    # Test API
    c = Client()
    url = f'/admin_dashboard/get_po_products/{po.id}'
    print(f"Calling API: {url}")
    
    response = c.get(url)
    
    if response.status_code != 200:
        print(f"FAIL: API returned status {response.status_code}")
        print(response.content)
        return
        
    data = json.loads(response.content)
    print("Response JSON:", data)
    
    products = data.get('products', [])
    prod_ids = [p['id'] for p in products]
    
    if len(products) != 2:
        print(f"FAIL: Expected 2 products, got {len(products)}")
    elif p1.id in prod_ids and p2.id in prod_ids and p3.id not in prod_ids:
        print("PASS: Verified API returns correct products for PO.")
    else:
        print(f"FAIL: Product IDs mismatch. Got {prod_ids}")
        
    # Cleanup
    po.delete()
    p1.delete()
    p2.delete()
    p3.delete()
    cat.delete()
    supplier.delete()

if __name__ == "__main__":
    test_api()
