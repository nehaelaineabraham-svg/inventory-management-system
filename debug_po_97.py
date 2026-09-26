import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventory.settings')
django.setup()

from inventory import models

def check_po_97():
    try:
        po_id = 97
        print(f"Checking PO {po_id}...")
        
        try:
            po = models.PurchaseOrders.objects.get(id=po_id)
            print(f"PO found: ID={po.id}, Supplier={po.supplier_id}, Date={po.po_date}, Status={po.status}")
        except models.PurchaseOrders.DoesNotExist:
            print("PO 97 does not exist.")
            return

        items = models.PurchaseOrderItems.objects.filter(po_id=po_id)
        count = items.count()
        print(f"Items count: {count}")
        
        for item in items:
            print(f" - Item ID: {item.id}, Product ID: {item.product_id}, Qty: {item.quantity}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_po_97()
