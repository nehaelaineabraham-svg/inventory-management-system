import os
import django
from django.test import Client

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventory.settings')
django.setup()

from django.conf import settings
settings.ALLOWED_HOSTS.append('testserver')

from inventory import models
from datetime import date

def test_po_refactor():
    print("Testing PO Refactor...")
    c = Client()
    
    # Setup Data
    cat = models.Categories.objects.create(cat_name="Test Cat PO", created_at=date.today())
    sup = models.Suppliers.objects.create(supplier_name="Test Sup", created_at=date.today())
    prod = models.Products.objects.create(cat_id=cat.id, product_name="Test Prod PO", unit="KG", price=50, created_at=date.today())
    
    # 1. Verify View Mode (Total Value)
    print("\n--- Testing View Mode ---")
    po1 = models.PurchaseOrders.objects.create(supplier_id=sup.id, status='pending', created_at=date.today())
    models.PurchaseOrderItems.objects.create(po=po1, product=prod, quantity=10, unit_price=50, total_price=500)
    
    resp = c.get('/admin_dashboard/purchase_orders/')
    content = resp.content.decode()
    if 'Purchse Orders' in content or 'Purchase Orders' in content: # Title check
        if 'Total Value' in content:
            print("PASS: Total Value column header found.")
        else:
            print("FAIL: Total Value column header NOT found.")
            
        if '500' in content: # 500.00 might be formatted
            print("PASS: PO Total Value (500) found in list.")
        else:
            print("FAIL: PO Total Value (500) NOT found.")
            
    # 2. Verify Add Mode (Unit, Grand Total)
    print("\n--- Testing Add Mode ---")
    resp = c.get('/admin_dashboard/add_purchase_order/')
    content = resp.content.decode()
    
    if '<th>Unit</th>' in content:
        print("PASS: Unit column found in Add Mode.")
    else:
        print("FAIL: Unit column NOT found in Add Mode.")
        
    if 'id="grandTotal"' in content:
        print("PASS: Grand Total display found in Add Mode.")
    else:
        print("FAIL: Grand Total display NOT found in Add Mode.")
        
    if 'data-unit="KG"' in content:
         print("PASS: Product option has data-unit attribute.")
    else:
         print("FAIL: Product option missing data-unit attribute.")

    # 3. Verify Edit Mode (No GRN)
    print("\n--- Testing Edit Mode (No GRN) ---")
    resp = c.get(f'/admin_dashboard/edit_purchase_order/{po1.id}')
    content = resp.content.decode()
    
    if 'value="KG"' in content:
        print("PASS: Unit value displayed in Edit Mode.")
    else:
        print("FAIL: Unit value NOT displayed in Edit Mode.")
        
    if 'readonly' in content and 'name="po_date"' in content and 'readonly' in content.split('name="po_date"')[1].split('>')[0]:
         print("FAIL: PO Date is READONLY but should be EDITABLE (No GRN).")
    else:
         print("PASS: PO Date is Editable (No GRN).")

    # 4. Verify Edit Mode (With GRN)
    print("\n--- Testing Edit Mode (With GRN) ---")
    # Create GRN
    models.Grn.objects.create(po_id=po1.id, product_id=prod.id, qty=10, created_at=date.today())
    
    resp = c.get(f'/admin_dashboard/edit_purchase_order/{po1.id}')
    content = resp.content.decode()
    
    if 'This PO has associated GRN entries' in content:
        print("PASS: Warning message shown.")
    else:
        print("FAIL: Warning message NOT shown.")
        
    # Check for disabled attributes
    if 'name="po_date"' in content and 'readonly' in content.split('name="po_date"')[1].split('>')[0]:
         print("PASS: PO Date is READONLY (Has GRN).")
    else:
         print("FAIL: PO Date is Editable but should be READONLY (Has GRN).")
         
    if 'name="product_id[]"' in content and 'disabled' in content.split('name="product_id[]"')[1].split('>')[0]:
         print("PASS: Product Select is DISABLED (Has GRN).")
    else:
         print("FAIL: Product Select is ENABLED but should be DISABLED (Has GRN).")
         print("FAIL: Product Select is ENABLED but should be DISABLED (Has GRN).")
         # Check if file writing works
         try:
             with open('d:\\inventory\\debug_content.html', 'w', encoding='utf-8') as f:
                 f.write(content)
             print("Saved content to d:\\inventory\\debug_content.html")
         except Exception as e:
             print(f"Could not save debug content: {e}")

    # Cleanup
    # models.Grn.objects.filter(po_id=po1.id).delete()
    # po1.delete()
    # prod.delete()
    # sup.delete()
    # cat.delete()

if __name__ == "__main__":
    test_po_refactor()
