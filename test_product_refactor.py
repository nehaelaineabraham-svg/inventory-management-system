import os
import django
from django.test import Client

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventory.settings')
django.setup()

from inventory import models
from datetime import date

def test_product_logic():
    print("Testing Product Logic...")
    
    # Setup
    cat = models.Categories.objects.create(cat_name="Test Cat", created_at=date.today())
    
    # 1. Test Delete Protection (Linked to PO)
    p1 = models.Products.objects.create(cat_id=cat.id, product_name="Linked PO Prod", price=100, created_at=date.today())
    po = models.PurchaseOrders.objects.create(status='pending', created_at=date.today())
    models.PurchaseOrderItems.objects.create(po=po, product=p1, quantity=1, unit_price=100, total_price=100)
    
    c = Client()
    resp = c.get(f'/admin_dashboard/delete_product/{p1.id}', follow=True)
    messages = list(resp.context['messages'])
    msg_texts = [m.message for m in messages]
    
    if any("Cannot delete" in m for m in msg_texts):
        print("PASS: Product linked to PO cannot be deleted.")
    else:
        print(f"FAIL: Product linked to PO was deleted or no error message. Msgs: {msg_texts}")
        
    # 2. Test Delete Protection (Linked to Stock/Sales)
    p2 = models.Products.objects.create(cat_id=cat.id, product_name="Linked Stock Prod", price=100, created_at=date.today())
    models.StockLedger.objects.create(product_id=p2.id, voucher_type='SALE', qty=1, created_at=date.today())
    
    resp = c.get(f'/admin_dashboard/delete_product/{p2.id}', follow=True)
    messages = list(resp.context['messages'])
    msg_texts = [m.message for m in messages]
    
    if any("Cannot delete" in m for m in msg_texts):
        print("PASS: Product linked to Stock/Sales cannot be deleted.")
    else:
        print(f"FAIL: Product linked to Stock was deleted. Msgs: {msg_texts}")

    # 3. Test Delete Success
    p3 = models.Products.objects.create(cat_id=cat.id, product_name="Fresh Prod", price=100, created_at=date.today())
    resp = c.get(f'/admin_dashboard/delete_product/{p3.id}', follow=True)
    
    if not models.Products.objects.filter(id=p3.id).exists():
        print("PASS: Unused product deleted successfully.")
    else:
        print("FAIL: Unused product NOT deleted.")

    # 4. Check Template Content (Static check)
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
    cat.delete()
    # p1, p2, p3 might be deleted or not, cleanup relies on cascade or manual if needed, 
    # but since tests run in transaction or we just leave garbage in dev DB... 
    # explicit cleanup for p1/p2 which failed delete
    if models.Products.objects.filter(id=p1.id).exists(): p1.delete()
    if models.Products.objects.filter(id=p2.id).exists(): p2.delete()

if __name__ == "__main__":
    test_product_logic()
