import os
import django
from django.utils import timezone
import random
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventory.settings')
django.setup()

from inventory.models import (
    Categories, Suppliers, Customers, Products, 
    PurchaseOrders, PurchaseOrderItems, Grn, Sales, StockLedger, Users
)

def populate():
    print("Starting data population...")

    # 1. Categories
    print("Creating Categories...")
    cats = ['Electronics', 'Home & Kitchen', 'Books', 'Clothing']
    created_cats = []
    for cat_name in cats:
        cat = Categories.objects.create(
            cat_name=cat_name,
            status=1,
            created_at=timezone.now()
        )
        created_cats.append(cat)
        print(f"  Created Category: {cat.cat_name}")

    # 2. Suppliers
    print("Creating Suppliers...")
    suppliers_data = [
        {'name': 'Tech World', 'email': 'contact@techworld.com', 'phone': '1234567890'},
        {'name': 'Home Goods Inc', 'email': 'sales@homegoods.com', 'phone': '0987654321'}
    ]
    created_suppliers = []
    for s_data in suppliers_data:
        supplier = Suppliers.objects.create(
            supplier_name=s_data['name'],
            email=s_data['email'],
            phone=s_data['phone'],
            address=f"123 {s_data['name']} St",
            created_at=timezone.now()
        )
        created_suppliers.append(supplier)
        print(f"  Created Supplier: {supplier.supplier_name}")

    # 3. Customers
    print("Creating Customers...")
    customers_data = [
        {'name': 'Alice Johnson', 'email': 'alice@example.com', 'phone': '5551234567'},
        {'name': 'Bob Smith', 'email': 'bob@example.com', 'phone': '5559876543'}
    ]
    created_customers = []
    for c_data in customers_data:
        customer = Customers.objects.create(
            customer_name=c_data['name'],
            email=c_data['email'],
            phone=c_data['phone'],
            place='Cityville',
            address='456 Customer Ln',
            created_at=timezone.now()
        )
        created_customers.append(customer)
        print(f"  Created Customer: {customer.customer_name}")

    # 4. Products
    print("Creating Products...")
    products_data = [
        {'name': 'Smartphone X', 'cat': created_cats[0], 'sku': 'ELEC-001', 'price': 699.99},
        {'name': 'Laptop Pro', 'cat': created_cats[0], 'sku': 'ELEC-002', 'price': 1299.99},
        {'name': 'Blender 3000', 'cat': created_cats[1], 'sku': 'HOME-001', 'price': 49.99}
    ]
    created_products = []
    for p_data in products_data:
        product = Products.objects.create(
            cat_id=p_data['cat'].id,
            product_name=p_data['name'],
            sku=p_data['sku'],
            unit='pcs',
            price=Decimal(p_data['price']),
            status=1,
            reorder_level=10,
            created_at=timezone.now()
        )
        created_products.append(product)
        print(f"  Created Product: {product.product_name}")

    # 5. Purchase Orders
    print("Creating Purchase Orders...")
    po = PurchaseOrders.objects.create(
        supplier_id=created_suppliers[0].id,
        po_date=timezone.now().date(),
        status='Pending'
    )
    print(f"  Created PO: ID {po.id} for {created_suppliers[0].supplier_name}")

    # 6. Purchase Order Items
    print("Creating PO Items...")
    product_to_order = created_products[0]
    qty = 50
    unit_price = product_to_order.price
    total_price = unit_price * qty
    
    PurchaseOrderItems.objects.create(
        po=po,  # Using ForeignKey object
        product=product_to_order, # Using ForeignKey object
        quantity=qty,
        unit_price=unit_price,
        total_price=total_price
    )
    print(f"  Added item {product_to_order.product_name} to PO {po.id}")

    # 7. GRN (Goods Received Note)
    print("Creating GRN...")
    Grn.objects.create(
        po_id=po.id,
        product_id=product_to_order.id,
        qty=qty,
        batch_no='BATCH001',
        location='Warehouse A',
        created_at=timezone.now()
    )
    print(f"  Created GRN for PO {po.id}")

    # 8. Sales
    print("Creating Sales...")
    sale = Sales.objects.create(
        customer_id=created_customers[0].id,
        sale_date=timezone.now().date(),
        created_at=timezone.now()
    )
    print(f"  Created Sale: ID {sale.id} for {created_customers[0].customer_name}")
    
    # 9. Stock Ledger
    print("Adding Stock Ledger Entry...")
    StockLedger.objects.create(
        product_id=product_to_order.id,
        voucher_type='GRN',
        voucher_id=po.id, 
        qty=qty,
        in_out='IN',
        batch_no='BATCH001',
        location='Warehouse A',
        created_at=timezone.now()
    )
    print("  Created Stock Ledger Entry (IN)")

    # Out entry for sale
    StockLedger.objects.create(
        product_id=product_to_order.id,
        voucher_type='Sale',
        voucher_id=sale.id,
        qty=1,
        in_out='OUT',
        batch_no='BATCH001',
        location='Warehouse A',
        created_at=timezone.now()
    )
    print("  Created Stock Ledger Entry (OUT)")
    
    # 10. Users
    print("Creating a test User...")
    if not Users.objects.filter(email='admin@inventory.com').exists():
        Users.objects.create(
            name='Test Admin',
            email='admin@inventory.com',
            password='password123', 
            role='Admin',
            status=1,
            created_at=timezone.now()
        )
        print("  Created User: Test Admin")
    else:
        print("  User 'Test Admin' already exists.")

    print("\nData population completed successfully!")

if __name__ == '__main__':
    populate()
