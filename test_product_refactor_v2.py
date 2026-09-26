import os
import django
from django.test import Client

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventory.settings')
django.setup()

from inventory import models
from datetime import date

def test_product_logic_v2():
    print("Testing Product Logic V2...")
    
    # Setup
    try:
        cat = models.Categories.objects.create(cat_name="Test Cat V2", created_at=date.today())
        
        # 1. Test Delete Protection (Linked to PO)
        print("Test 1: Delete Product linked to PO")
        p1 = models.Products.objects.create(cat_id=cat.id, product_name="Linked PO Prod V2", price=100, created_at=date.today())
        po = models.PurchaseOrders.objects.create(status='pending', created_at=date.today())
        models.PurchaseOrderItems.objects.create(po=po, product=p1, quantity=1, unit_price=100, total_price=100)
        
        c = Client()
        c.get(f'/admin_dashboard/delete_product/{p1.id}')
        
        if models.Products.objects.filter(id=p1.id).exists():
            print("PASS: Product linked to PO was NOT deleted.")
        else:
            print("FAIL: Product linked to PO WAS deleted.")
            
        # 2. Test Delete Protection (Linked to Stock/Sales)
        print("Test 2: Delete Product linked to Stock")
        p2 = models.Products.objects.create(cat_id=cat.id, product_name="Linked Stock Prod V2", price=100, created_at=date.today())
        models.StockLedger.objects.create(product_id=p2.id, voucher_type='SALE', qty=1, created_at=date.today())
        
        c.get(f'/admin_dashboard/delete_product/{p2.id}')
        
        if models.Products.objects.filter(id=p2.id).exists():
            print("PASS: Product linked to Stock was NOT deleted.")
        else:
            print("FAIL: Product linked to Stock WAS deleted.")

        # 3. Test Delete Success
        print("Test 3: Delete Unused Product")
        p3 = models.Products.objects.create(cat_id=cat.id, product_name="Fresh Prod V2", price=100, created_at=date.today())
        c.get(f'/admin_dashboard/delete_product/{p3.id}')
        
        if not models.Products.objects.filter(id=p3.id).exists():
            print("PASS: Unused product deleted successfully.")
        else:
            print("FAIL: Unused product NOT deleted.")

        # 4. Check Template Content (Static check)
        print("Test 4: Template Content")
        with open('d:\\inventory\\Templates\\products\\products.html', 'r') as f:
            content = f.read()
            if 'id="addProductModal"' in content and 'Proposed Selling Price' in content:
                 print("PASS: products.html has Modal and Correct Label.")
            else:
                 print("FAIL: products.html missing Modal or Label.")

        with open('d:\\inventory\\Templates\\products\\products_edit.html', 'r') as f:
            content = f.read()
            if 'name="sku" value="{{product.sku}}" readonly' in content:
                print("PASS: products_edit.html has Readonly SKU.")
            else:
                print("FAIL: products_edit.html missing Readonly SKU.")
                
        # Cleanup
        po.delete()
        if models.Products.objects.filter(id=p1.id).exists(): p1.delete()
        if models.Products.objects.filter(id=p2.id).exists(): p2.delete()
        cat.delete()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_product_logic_v2()
