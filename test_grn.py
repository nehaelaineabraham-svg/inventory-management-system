import os
import django
from django.test import Client, RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventory.settings')
django.setup()

from inventory import models
from admin.views import save_grn, update_grn
import datetime

def setup_test_data():
    # Create Supplier
    sup, _ = models.Suppliers.objects.get_or_create(
        supplier_name="GRN Test Supplier",
        email="grntest@example.com",
        created_at=datetime.datetime.now()
    )
    
    # Create Products
    p1, _ = models.Products.objects.get_or_create(product_name="GRN Prod 1", price=10.00, created_at=datetime.datetime.now())
    p2, _ = models.Products.objects.get_or_create(product_name="GRN Prod 2", price=20.00, created_at=datetime.datetime.now())
    
    # Create PO
    po = models.PurchaseOrders.objects.create(
        supplier_id=sup.id,
        po_date=datetime.date.today(),
        status='pending'
    )
    
    return po, p1, p2

def test_grn_workflow():
    print("Setting up test data...")
    po, p1, p2 = setup_test_data()
    print(f"PO ID: {po.id}")
    
    # --- TEST 1: SAVE GRN (Multi-Item) ---
    print("\nTest 1: Saving Multi-Item GRN...")
    factory = RequestFactory()
    
    post_data = {
        'po_id': po.id,
        'product_id[]': [p1.id, p2.id],
        'qty[]': [10, 5],
        'batch_no[]': ['B1', ''],
        'location[]': ['Loc A', 'Loc B']
    }
    
    request = factory.post('/admin/save_grn/', post_data)
    
    # Middleware
    middleware = SessionMiddleware(lambda x: None)
    middleware.process_request(request)
    request.session.save()
    messages = MessageMiddleware(lambda x: None)
    messages.process_request(request)
    
    response = save_grn(request)
    
    # Verify DB
    grns = models.Grn.objects.filter(po_id=po.id)
    print(f"GRN Count for PO {po.id}: {grns.count()}")
    if grns.count() == 2:
        print("PASS: 2 GRN records created.")
    else:
        print("FAIL: Incorrect GRN count.")
        return

    # Check Stock Ledger
    stocks = models.StockLedger.objects.filter(voucher_type='GRN', voucher_id__in=grns.values_list('id', flat=True))
    print(f"Stock Ledger Entries: {stocks.count()}")
    if stocks.count() == 2:
        print("PASS: Stock Ledger entries created.")
    else:
        print("FAIL: Stock Ledger missing.")

    # --- TEST 2: UPDATE GRN (Edit Collection) ---
    print("\nTest 2: Updating GRN Collection (Delete 1, Update 1, Add 1)...")
    
    # Simulate Form: Keep p1 (qty 15), Remove p2, Add p1 again (different batch - usually same product different batch is separate row)
    # Actually let's just: Update p1 qty to 15, Remove p2.
    
    post_data_update = {
        'po_id': po.id,
        'product_id[]': [p1.id],
        'qty[]': [15],
        'batch_no[]': [''],
        'location[]': ['Loc A']
    }
    
    request_upd = factory.post('/admin/update_grn/', post_data_update)
    middleware.process_request(request_upd)
    request_upd.session.save()
    messages.process_request(request_upd)
    
    response_upd = update_grn(request_upd)
    
    # Verify DB
    grns_final = models.Grn.objects.filter(po_id=po.id)
    print(f"Final GRN Count: {grns_final.count()}")
    
    if grns_final.count() == 1:
        item = grns_final.first()
        print(f"Item: Prod={item.product_id}, Qty={item.qty}, Batch={item.batch_no}")
        if item.product_id == p1.id and item.qty == 15 and item.batch_no == 'B1-UPDATED':
            print("PASS: GRN collection updated correctly.")
        else:
            print("FAIL: Updated item details incorrect.")
    else:
        print("FAIL: Final GRN count incorrect.")

if __name__ == '__main__':
    try:
        test_grn_workflow()
    except Exception as e:
        print(f"An error occurred: {e}")
