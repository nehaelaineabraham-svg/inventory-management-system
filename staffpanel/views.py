from django.shortcuts import render, redirect
from django.contrib import messages
from inventory import models
from django.db import connection
from django.core.paginator import Paginator
from django.db.models import Sum
from django.http import JsonResponse, HttpResponse
import datetime
import csv


# Middleware check for staff role
def check_staff_session(request):
    user_type = request.session.get('usertype', '').lower()
    if user_type != 'staff':
        messages.error(request, 'Access denied! Staff login required.')
        return redirect('/login/')
    return None


# Staff Dashboard
def staff_dashboard(request):
    check = check_staff_session(request)
    if check:
        return check
    
    user_id = request.session.get('user_id')
    
    # Get counts for staff's own transactions
    total_grns = models.Grn.objects.count()
    total_sales = models.Sales.objects.count()
    total_products = models.Products.objects.count()
    
    # Alerts count
    cursor = connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM products WHERE stock_qty < reorder_level")
    low_stock_count = cursor.fetchone()[0]
    
    context = {
        'total_grns': total_grns,
        'total_sales': total_sales,
        'total_products': total_products,
        'low_stock_count': low_stock_count,
        'expiry_count': 0,
        'user_name': request.session.get('name', 'Staff'),
        'user_role': 'STAFF'
    }
    return render(request, 'staffpanel/staff_dashboard.html', context)


# View Products (Read-only)
def view_products(request):
    check = check_staff_session(request)
    if check:
        return check
    
    product_search = request.GET.get('product_search', '')
    
    query = """
        SELECT p.id, p.product_name, c.cat_name, p.sku, u.unit_name, p.price, p.status
        FROM products p
        LEFT JOIN categories c ON p.cat_id = c.id
        LEFT JOIN unit u ON p.unit_id = u.unit_id
    """
    
    params = []
    if product_search:
        query += " WHERE p.product_name LIKE %s"
        search_val = f"{product_search}%"
        params = [search_val]
        
    query += " ORDER BY p.id DESC"
    
    cursor = connection.cursor()
    cursor.execute(query, params)
    products_list = cursor.fetchall()
    
    paginator = Paginator(products_list, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'products': page_obj.object_list,
        'page_obj': page_obj,
        'product_search': product_search,
        'user_name': request.session.get('name', 'Staff'),
        'user_role': 'STAFF'
    }
    
    if request.GET.get('ajax'):
        return render(request, 'staffpanel/products_table_partial.html', context)
        
    return render(request, 'staffpanel/products_view.html', context)


# Enter GRN (Stock IN)
def enter_grn(request):
    check = check_staff_session(request)
    if check:
        return check
    
    # Get approved POs for dropdown (status_id=2)
    pos = models.PurchaseOrders.objects.filter(status_id=2).order_by('-id')
    
    # Generate a dummy GRN number (not strictly needed by backend but used in template)
    last_grn = models.Grn.objects.order_by('-id').first()
    grn_no = f"GRN-{(last_grn.id + 1 if last_grn else 1):06d}"
    
    context = {
        'purchase_orders': pos,
        'grn_no': grn_no,
        'user_name': request.session.get('name', 'Staff'),
        'user_role': 'STAFF'
    }
    return render(request, 'staffpanel/enter_grn.html', context)


# AJAX endpoint to get PO items for GRN entry
def staff_view_po_items_for_grn(request, poid):
    check = check_staff_session(request)
    if check:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
        
    try:
        po = models.PurchaseOrders.objects.get(id=poid, status_id=2)
        supplier = models.Suppliers.objects.get(id=po.supplier_id)
        items = models.PurchaseOrderItems.objects.filter(po_id=poid)
        
        data = []
        for item in items:
            # Calculate already received quantity for this product in this PO
            received_data = models.GRNItems.objects.filter(
                grn__po_id=poid, 
                product_id=item.product.id
            ).aggregate(total_received=Sum('quantity'))
            
            already_received = received_data['total_received'] or 0
            remaining_qty = item.quantity - already_received
            
            data.append({
                'product_id': item.product.id,
                'product_name': item.product.product_name,
                'ordered_qty': item.quantity,
                'already_received': already_received,
                'remaining_qty': remaining_qty,
                'unit': item.product.unit_id,
                'unit_name': item.unit.unit_name if item.unit else '-',
                'rate': float(item.unit_price),
                'total': 0.0,
                'is_completed': remaining_qty <= 0
            })
        return JsonResponse({'supplier': supplier.supplier_name, 'products': data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# Staff GRN List
def staff_grn_list(request):
    check = check_staff_session(request)
    if check:
        return check
    
    # Get all GRNs - one row per GRN header (matches admin structure)
    cursor = connection.cursor()
    cursor.execute("""
        SELECT g.id, g.grn_date, g.po_id, po.po_date, sup.supplier_name,
               COALESCE(SUM(gi.grn_amount), 0) as total,
               g.status_id, s.status
        FROM grn g
        LEFT JOIN purchase_orders po ON g.po_id = po.id
        LEFT JOIN suppliers sup ON po.supplier_id = sup.id
        LEFT JOIN grn_items gi ON g.id = gi.grn_id
        LEFT JOIN status s ON g.status_id = s.id
        GROUP BY g.id, g.grn_date, g.po_id, po.po_date, sup.supplier_name, g.status_id, s.status
        ORDER BY g.id DESC
    """)
    grns_list = cursor.fetchall()
    
    paginator = Paginator(grns_list, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'grns': page_obj.object_list,
        'page_obj': page_obj,
        'user_name': request.session.get('name', 'Staff'),
        'user_role': 'STAFF'
    }

    if request.GET.get('ajax'):
        return render(request, 'staffpanel/grn_table_partial.html', context)
        
    return render(request, 'staffpanel/grn_list.html', context)


# View GRN Items (Detailed View for Staff)
def staff_view_grn_items(request, gid):
    check = check_staff_session(request)
    if check:
        return check
        
    # Get GRN header data
    cursorgrn = connection.cursor()
    cursorgrn.execute("""
        SELECT g.id, g.grn_date, g.po_id, po.po_date, sup.id, sup.supplier_name, s.status
        FROM grn g
        LEFT JOIN purchase_orders po ON g.po_id = po.id
        LEFT JOIN suppliers sup ON po.supplier_id = sup.id
        LEFT JOIN status s ON g.status_id = s.id
        WHERE g.id = %s
    """, [gid])
    grn_raw = cursorgrn.fetchone()
    
    if not grn_raw:
        messages.error(request, 'GRN not found.')
        return redirect('staff_grn_list')
        
    grn_data = {
        'id': grn_raw[0],
        'grn_date': grn_raw[1],
        'po_id': grn_raw[2],
        'po_date': grn_raw[3],
        'supplier_id': grn_raw[4],
        'supplier_name': grn_raw[5],
        'status': grn_raw[6]
    }
    
    # Get GRN items
    cursor = connection.cursor()
    cursor.execute("""
        SELECT gi.product_id, p.product_name, gi.quantity, gi.rate, gi.grn_amount, u.unit_name
        FROM grn_items gi
        LEFT JOIN products p ON gi.product_id = p.id
        LEFT JOIN unit u ON p.unit_id = u.unit_id
        WHERE gi.grn_id = %s
    """, [gid])
    items_raw = cursor.fetchall()
    
    items = []
    grand_total = 0
    for row in items_raw:
        item = {
            'product_id': row[0],
            'product_name': row[1],
            'quantity': row[2],
            'unit_price': row[3],
            'total_price': row[4],
            'unit_name': row[5]
        }
        items.append(item)
        grand_total += float(row[4]) if row[4] else 0
        
    context = {
        'grn': grn_data,
        'items': items,
        'grand_total': grand_total,
        'user_name': request.session.get('name', 'Staff'),
        'user_role': 'STAFF'
    }
    return render(request, 'staffpanel/view_grn_items.html', context)


# Staff Sales List
def staff_sales_list(request):
    check = check_staff_session(request)
    if check:
        return check
    
    sale_search = request.GET.get('sale_search', '')
    
    # Get all sales with Total Amount
    query = """
        SELECT s.id, s.sale_date, c.customer_name, s.created_at, st.status,
               COALESCE(SUM(si.total), 0) as grand_total
        FROM sales s
        LEFT JOIN customers c ON s.customer_id = c.id
        LEFT JOIN sale_items si ON s.id = si.sale_id
        LEFT JOIN status st ON s.status_id = st.id
    """
    params = []
    
    if sale_search:
        query += " WHERE c.customer_name LIKE %s OR s.id LIKE %s"
        params = [f"{sale_search}%", f"{sale_search}%"]
        
    query += " GROUP BY s.id, s.sale_date, c.customer_name, s.created_at, st.status ORDER BY s.id DESC"
    
    cursor = connection.cursor()
    cursor.execute(query, params)
    sales_list = cursor.fetchall()
    
    paginator = Paginator(sales_list, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'sales': page_obj.object_list,
        'page_obj': page_obj,
        'sale_search': sale_search,
        'user_name': request.session.get('name', 'Staff'),
        'user_role': 'STAFF'
    }

    if request.GET.get('ajax'):
        return render(request, 'staffpanel/sales_table_partial.html', context)
        
    return render(request, 'staffpanel/sales_list.html', context)


# View Sale Items (Detailed View for Staff)
def staff_view_sale_items(request, sid):
    check = check_staff_session(request)
    if check:
        return check
        
    # Get Sale header data
    cursor = connection.cursor()
    cursor.execute("""
        SELECT s.id, s.sale_date, c.customer_name, st.status, s.created_at
        FROM sales s
        LEFT JOIN customers c ON s.customer_id = c.id
        LEFT JOIN status st ON s.status_id = st.id
        WHERE s.id = %s
    """, [sid])
    sale_raw = cursor.fetchone()
    
    if not sale_raw:
        messages.error(request, 'Sale not found.')
        return redirect('staff_sales_list')
        
    sale_data = {
        'id': sale_raw[0],
        'sale_date': sale_raw[1],
        'customer_name': sale_raw[2],
        'status': sale_raw[3],
        'created_at': sale_raw[4]
    }
    
    # Get Sale items
    cursor.execute("""
        SELECT si.product_id, p.product_name, si.qty, si.price, si.total, u.unit_name
        FROM sale_items si
        LEFT JOIN products p ON si.product_id = p.id
        LEFT JOIN unit u ON p.unit_id = u.unit_id
        WHERE si.sale_id = %s
    """, [sid])
    items_raw = cursor.fetchall()
    
    items = []
    grand_total = 0
    for row in items_raw:
        item = {
            'product_id': row[0],
            'product_name': row[1],
            'quantity': row[2],
            'unit_price': row[3],
            'total_price': row[4],
            'unit_name': row[5]
        }
        items.append(item)
        grand_total += float(row[4]) if row[4] else 0
        
    context = {
        'sale': sale_data,
        'items': items,
        'grand_total': grand_total,
        'user_name': request.session.get('name', 'Staff'),
        'user_role': 'STAFF'
    }
    return render(request, 'staffpanel/view_sale_items.html', context)


# Save GRN
# Save GRN (Master-Detail Structure)
def save_grn(request):
    check = check_staff_session(request)
    if check:
        return check
    
    if request.method == "POST":
        grn_date = request.POST.get("grn_date")
        po_id = request.POST.get("po_id")
        
        # Save Master GRN
        grn = models.Grn(
            grn_date=grn_date,
            po_id=po_id,
            status_id=1, # 1 = Pending
            created_at=datetime.datetime.now()
        )
        grn.save()
        
        # Save Items
        product_ids = request.POST.getlist('product_id[]')
        quantities = request.POST.getlist('quantity[]')
        poqs = request.POST.getlist('poq[]')
        bals = request.POST.getlist('bal[]')
        units_sent = request.POST.getlist('unit[]')
        prices = request.POST.getlist('rate[]')
        
        items_count = 0
        for i in range(len(product_ids)):
            if i < len(quantities) and quantities[i] and int(quantities[i]) > 0:
                qty = int(quantities[i])
                price = float(prices[i]) if i < len(prices) else 0
                total = qty * price
                poq = int(poqs[i]) if i < len(poqs) else 0
                balq = int(bals[i]) if i < len(bals) else 0
                unit_id = units_sent[i] if i < len(units_sent) else None
                
                models.GRNItems.objects.create(
                    grn=grn,
                    product_id=product_ids[i],
                    po_qty=poq,
                    bal_qty=balq,
                    quantity=qty,
                    rate=price,
                    grn_amount=total,
                    unit_id=unit_id
                )
                items_count += 1
        
        if items_count > 0:
            messages.success(request, f'GRN-{grn.id:06d} created successfully with {items_count} items.')
        else:
            # If no items were actually saved, might want to delete the master or warn
            messages.warning(request, 'GRN created but no items were added.')
            
        return redirect('staff_grn_list')
    
    return redirect('staff_enter_grn')


# Approve GRN (Stock Entry)



# Edit GRN (View - Shows all Pending items for this PO)
# Edit GRN (View - Detailed view for a specific GRN)
def edit_grn(request, gid):
    check = check_staff_session(request)
    if check: return check
    
    try:
        grn = models.Grn.objects.get(id=gid)
        if grn.status_id == 2:  # 2 = Approved
            messages.error(request, 'Cannot edit Approved GRN.')
            return redirect('staff_grn_list')
            
        # Fetch actual items for this GRN
        items = models.GRNItems.objects.filter(grn_id=gid)
        products = models.Products.objects.all()
        units = models.Units.objects.all()
        
        # Get status object
        status_obj = models.DocStatus.objects.get(id=grn.status_id)
        
        # Get PO and Supplier
        po = models.PurchaseOrders.objects.get(id=grn.po_id)
        supplier = models.Suppliers.objects.get(id=po.supplier_id)
        
        context = {
            "grn": grn,
            "grn_list": items, 
            "products": products,
            "units": units,
            "status": status_obj,
            "po": po,
            "supplier": supplier,
            'user_name': request.session.get('name', 'Staff'),
            'user_role': 'STAFF'
        }
        return render(request, 'staffpanel/edit_grn.html', context)
        
    except models.Grn.DoesNotExist:
        messages.error(request, 'GRN not found.')
        return redirect('staff_grn_list')


# Update GRN (Save - Handles Multiple Items)
# Update GRN (Save - Handles Multiple Items safely)
def update_grn(request):
    check = check_staff_session(request)
    if check: return check
    
    if request.method == "POST":
        item_ids = request.POST.getlist('grn_id[]')
        product_ids = request.POST.getlist('product_id[]')
        qtys = request.POST.getlist('qty[]')
        
        updated_count = 0
        for i in range(len(item_ids)):
            try:
                item = models.GRNItems.objects.get(id=item_ids[i])
                # Check master status
                if item.grn.status_id == 2: # Approved
                    continue
                    
                item.product_id = product_ids[i]
                item.quantity = int(qtys[i]) if qtys[i] else 0
                item.grn_amount = float(item.rate or 0) * float(item.quantity)
                item.save()
                updated_count += 1
            except Exception as e:
                print(f"Error updating item {item_ids[i]}: {e}")
                continue
                
        messages.success(request, f'Updated {updated_count} GRN items successfully.')
            
    return redirect('staff_grn_list')


# Delete GRN (Only if Pending)
def delete_grn(request, gid):
    check = check_staff_session(request)
    if check: return check
    
    try:
        grn = models.Grn.objects.get(id=gid)
        if grn.status_id == 2:  # 2 = Approved
            messages.error(request, 'Cannot delete Approved GRN. Stock already updated.')
            return redirect('staff_grn_list')
            
        grn.delete()
        messages.success(request, 'GRN deleted successfully.')
        
    except models.Grn.DoesNotExist:
        messages.error(request, 'GRN not found.')
        
    return redirect('staff_grn_list')


# Create Sales (Stock OUT)
def create_sales(request):
    check = check_staff_session(request)
    if check:
        return check
    
    # Calculate next Sale Number
    last_sale = models.Sales.objects.latest('id') if models.Sales.objects.exists() else None
    next_id = (last_sale.id + 1) if last_sale else 1
    sale_number = f"SALE-{next_id:06d}"
    
    # Fetch products with accurate stock using raw SQL
    from django.db import connection
    cursorprod = connection.cursor()
    cursorprod.execute("""
        SELECT p.id, p.product_name, p.price, p.unit_id, p.stock_qty
        FROM products p
    """)
    prod_raw = cursorprod.fetchall() 

    products = []     
    for row in prod_raw:
        item = {
            'id': row[0], 
            'product_name': row[1],
            'price': row[2],
            'unit_id': row[3],
            'stock_qty': row[4]
        }
        products.append(item)
    
    context = {
        'customers': models.Customers.objects.all(),
        'products': products,
        'units': models.Units.objects.all(),
        'sale_number': sale_number,
        'user_name': request.session.get('name', 'Staff'),
        'user_role': 'STAFF'
    }
    return render(request, 'staffpanel/create_sales.html', context)


# Save Sale
def save_sale(request):
    check = check_staff_session(request)
    if check:
        return check
    
    customer_id = request.POST["customer_id"]
    sale_date = request.POST["sale_date"]
    
    product_ids = request.POST.getlist("product_id[]")
    qtys = request.POST.getlist("qty[]")
    
    import datetime
    
    # Save Sale Header (Approved)
    sale = models.Sales(
        customer_id=customer_id,
        sale_date=sale_date,
        status_id=2, # 2 = Approved (Auto-approve)
        created_at=datetime.datetime.now()
    )
    sale.save()
    
    # Loop through items, save to SaleItems and deduct stock
    for i in range(len(product_ids)):
        if i >= len(qtys): break
        pid = product_ids[i]
        qty = qtys[i]
        
        if not pid or not qty: continue
        
        # Get price for record
        try:
            prod = models.Products.objects.get(id=pid)
            price = prod.price or 0
            
            # Save Sale Item
            total = float(price) * float(qty)
            item = models.SaleItems(
                sale_id=sale.id,
                product_id=pid,
                qty=qty,
                price=price,
                total=total
            )
            item.save()

            # Process stock deduction immediately (Auto-approve flow)
            # Create Stock Ledger OUT entry
            models.StockLedger.objects.create(
                product_id=pid,
                voucher_type='SALE',
                voucher_id=sale.id,
                qty=qty,
                in_out='OUT',
                created_at=datetime.datetime.now()
            )
            
            # Update Product Stock (Decrease)
            prod.stock_qty = (prod.stock_qty or 0) - int(qty)
            prod.save()

        except models.Products.DoesNotExist:
            continue
    
    messages.success(request, f'Sale created and approved successfully! Stock has been deducted.')
    return redirect('staff_sales_list')


# Approve Sale
def approve_sale(request, sid):
    check = check_staff_session(request)
    if check: return check
    
    try:
        sale = models.Sales.objects.get(id=sid)
        if sale.status_id == 2:
            messages.warning(request, 'Sale already approved.')
            return redirect('staff_sales_list')
            
        items = models.SaleItems.objects.filter(sale_id=sale.id)
        
        # Check Stock Availability First
        for item in items:
            prod = models.Products.objects.get(id=item.product_id)
            current_stock = prod.stock_qty if prod.stock_qty is not None else 0
            if current_stock < item.qty:
                messages.error(request, f'Insufficient stock for {prod.product_name}. Available: {current_stock}, Required: {item.qty}')
                return redirect('staff_sales_list')
        
        # If all good, process stock deduction
        for item in items:
            # Create Stock Ledger OUT entry (The "Posted" Record)
            stock = models.StockLedger(
                product_id=item.product_id,
                voucher_type='SALE',
                voucher_id=sale.id,
                qty=item.qty,
                in_out='OUT',
                created_at=datetime.datetime.now()
            )
            stock.save()
            
            # Update Product Stock (Decrease)
            prod = models.Products.objects.get(id=item.product_id)
            prod.stock_qty = (prod.stock_qty or 0) - int(item.qty)
            prod.save()
            
        # Update Status
        sale.status_id = 2
        sale.save()
        
        messages.success(request, 'Sale Approved and Stock Deducted successfully.')
        
    except models.Sales.DoesNotExist:
        messages.error(request, 'Sale not found.')
        
    return redirect('staff_sales_list')


# Delete Sale (Only Pending)
def delete_sale(request, sid):
    check = check_staff_session(request)
    if check: return check
    
    try:
        sale = models.Sales.objects.get(id=sid)
        if sale.status_id == 2:
            messages.error(request, 'Cannot delete Approved Sale.')
            return redirect('staff_sales_list')
            
        # Delete items first (though cascade might handle it if set, manual is safer here)
        models.SaleItems.objects.filter(sale_id=sale.id).delete()
        sale.delete()
        
        messages.success(request, 'Sale deleted successfully.')
        
    except models.Sales.DoesNotExist:
        messages.error(request, 'Sale not found.')
        
    return redirect('staff_sales_list')


# Edit Sale (View)
def edit_sale(request, sid):
    check = check_staff_session(request)
    if check: return check
    
    try:
        sale = models.Sales.objects.get(id=sid)
        if sale.status_id == 2:
            messages.error(request, 'Cannot edit Approved Sale.')
            return redirect('staff_sales_list')
            
        items = models.SaleItems.objects.filter(sale_id=sale.id)
        products = models.Products.objects.all()
        customers = models.Customers.objects.all()
        
        context = {
            'sale': sale,
            'sale_items': items,
            'products': products,
            'customers': customers,
            'user_name': request.session.get('name', 'Staff'),
            'user_role': 'STAFF'
        }
        return render(request, 'staffpanel/edit_sale.html', context)
        
    except models.Sales.DoesNotExist:
        messages.error(request, 'Sale not found.')
        return redirect('staff_sales_list')


# Update Sale (Save)
def update_sale(request):
    check = check_staff_session(request)
    if check: return check
    
    if request.method == "POST":
        sid = request.POST['sale_id']
        try:
            sale = models.Sales.objects.get(id=sid)
            if sale.status_id == 2:
                messages.error(request, 'Cannot update Approved Sale.')
                return redirect('staff_sales_list')
            
            # Update Header
            sale.customer_id = request.POST['customer_id']
            sale.sale_date = request.POST['sale_date']
            sale.save()
            
            # Update Items
            item_ids = request.POST.getlist('item_id[]')
            product_ids = request.POST.getlist('product_id[]')
            qtys = request.POST.getlist('qty[]')
            
            updated_count = 0
            
            for i in range(len(item_ids)):
                iid = item_ids[i]
                try:
                    item = models.SaleItems.objects.get(id=iid)
                    # Security check: item must belong to sale
                    if item.sale_id != sale.id: continue
                    
                    item.product_id = product_ids[i]
                    item.qty = qtys[i]
                    
                    # Update totals
                    prod = models.Products.objects.get(id=item.product_id)
                    item.price = prod.price or 0
                    item.total = float(item.price) * float(item.qty)
                    
                    item.save()
                    updated_count += 1
                except:
                    continue
                    
            messages.success(request, f'Sale updated successfully. {updated_count} items updated.')
            
        except models.Sales.DoesNotExist:
            messages.error(request, 'Sale not found.')
            
    return redirect('staff_sales_list')


# Delete Sale Item (Individual)
def delete_sale_item(request, item_id):
    check = check_staff_session(request)
    if check: return check
    
    try:
        item = models.SaleItems.objects.get(id=item_id)
        sale = models.Sales.objects.get(id=item.sale_id)
        
        if sale.status_id == 2:
            messages.error(request, 'Cannot delete item from Approved Sale.')
            return redirect('staff_edit_sale', sid=sale.id)
            
        item.delete()
        messages.success(request, 'Item removed from sale.')
        return redirect('staff_edit_sale', sid=sale.id)
        
    except:
        messages.error(request, 'Item not found.')
        return redirect('staff_sales_list')


# View Own Transactions
def view_transactions(request):
    check = check_staff_session(request)
    if check:
        return check
    
    # Get all stock ledger entries
    cursor = connection.cursor()
    cursor.execute("""
        SELECT 
            sl.id,
            sl.voucher_type,
            sl.voucher_id,
            p.product_name,
            sl.qty,
            sl.in_out,
            sl.created_at
        FROM stock_ledger sl
        LEFT JOIN products p ON sl.product_id = p.id
        ORDER BY sl.created_at DESC
    """)
    transaction_data = cursor.fetchall()
    
    # Handle pagination
    paginator = Paginator(transaction_data, 10)  # Show 10 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'transactions': page_obj.object_list,
        'user_name': request.session.get('name', 'Staff'),
        'user_role': 'STAFF'
    }
    return render(request, 'staffpanel/view_transactions.html', context)


def export_transactions_csv(request):
    check = check_staff_session(request)
    if check:
        return check
        
    cursor = connection.cursor()
    cursor.execute("""
        SELECT 
            sl.id,
            sl.voucher_type,
            sl.voucher_id,
            p.product_name,
            sl.qty,
            sl.in_out,
            sl.created_at
        FROM stock_ledger sl
        LEFT JOIN products p ON sl.product_id = p.id
        ORDER BY sl.created_at DESC
    """)
    rows = cursor.fetchall()

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="transactions_report_{datetime.date.today()}.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Type', 'Voucher ID', 'Product', 'Quantity', 'IN/OUT', 'Date'])

    for row in rows:
        # Format date for CSV
        formatted_row = list(row)
        if formatted_row[6]:
            formatted_row[6] = formatted_row[6].strftime('%Y-%m-%d %H:%M:%S')
        writer.writerow(formatted_row)

    return response


# Logout
def staff_logout(request):
    request.session.flush()
    messages.success(request, 'Logged out successfully!')
    return redirect('/login/')


# View Categories
def view_categories(request):
    check = check_staff_session(request)
    if check:
        return check
        
    category_search = request.GET.get('category_search', '')
    
    query = "SELECT id, cat_name, status FROM categories"
    params = []
    
    if category_search:
        query += " WHERE cat_name LIKE %s"
        params = [f"{category_search}%"]
        
    query += " ORDER BY id DESC"
    
    cursor = connection.cursor()
    cursor.execute(query, params)
    categories_list = cursor.fetchall()
    
    # Paginate (10 per page)
    paginator = Paginator(categories_list, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'categories': page_obj.object_list,
        'page_obj': page_obj,
        'category_search': category_search,
        'user_name': request.session.get('name', 'Staff'),
        'user_role': 'STAFF'
    }
    
    if request.GET.get('ajax'):
        return render(request, 'staffpanel/categories_table_partial.html', context)
        
    return render(request, 'staffpanel/categories_view.html', context)


# Report Damaged Items (Stock Adjustment - OUT)
def report_damaged_items(request):
    check = check_staff_session(request)
    if check:
        return check
        
    if request.method == "POST":
        product_id = request.POST['product_id']
        qty = int(request.POST['qty'])
        reason = request.POST['reason']
        
        # Create Stock Ledger OUT entry (Damage)
        stock = models.StockLedger(
            product_id=product_id,
            voucher_type='DAMAGE',
            voucher_id=0, # No specific voucher ID for manual damage report
            qty=qty,
            in_out='OUT',
            created_at=datetime.datetime.now()
        )
        stock.save()
        
        # Update Product Stock (Decrease for Damage)
        prod = models.Products.objects.get(id=product_id)
        prod.stock_qty = (prod.stock_qty or 0) - int(qty)
        prod.save()
        
        # Log Activity
        models.AuditLogs.objects.create(
            user_id=request.session.get('user_id'),
            action='REPORT_DAMAGE',
            table_name='stock_ledger',
            record_id=stock.id,
            created_at=datetime.datetime.now()
        )
        
        messages.success(request, 'Damaged items reported and stock updated.')
        return redirect('staff_damage_report')
        
    products = models.Products.objects.all()
    context = {
        'products': products,
        'user_name': request.session.get('name', 'Staff'),
        'user_role': 'STAFF'
    }
    return render(request, 'staffpanel/damage_report.html', context)


# Manual Stock Adjustment (Update Stock Quantity - Saves as PENDING)
def update_stock_quantity(request):
    check = check_staff_session(request)
    if check:
        return check
        
    if request.method == "POST":
        product_id = request.POST['product_id']
        unit_id = request.POST.get('unit_id')
        qty = int(request.POST['qty'])
        action_type = request.POST['action_type'] # ADD or REMOVE
        reason = request.POST.get('reason', '')
        
        # Save to StockAdjustment table as PENDING (status_id=1)
        adjustment = models.StockAdjustment(
            product_id=product_id,
            unit_id=unit_id,
            qty=qty,
            action_type=action_type,
            reason=reason,
            status_id=1, # 1 = Pending
            created_at=datetime.datetime.now(),
            created_by=request.session.get('user_id')
        )
        adjustment.save()
        
        messages.success(request, 'Stock adjustment request submitted and is pending manager approval.')
        return redirect('staff_stock_adjustment')

    products = models.Products.objects.all()
    units = models.Units.objects.all()
    context = {
        'products': products,
        'units': units,
        'user_name': request.session.get('name', 'Staff'),
        'user_role': 'STAFF'
    }
    return render(request, 'staffpanel/stock_adjustment.html', context)


# Generate Sales Invoice (View)
def generate_sales_invoice(request, sale_id):
    check = check_staff_session(request)
    if check:
        return check
        
    sale = models.Sales.objects.get(id=sale_id)
    customer = models.Customers.objects.get(id=sale.customer_id)
    
    # Get Items from StockLedger linked to this Sale
    # Assuming one sale = one or more items. But structure seems to be 1 Sale row = ??? 
    # Current save_sale only saves ONE product per Sale ID? 
    # Looking at save_sale: yes, it takes product_id and qty. So it's a single item sale currently.
    # To support multi-item sales, the model structure would need Sales -> SaleItems. 
    # For now, following existing pattern: One Sale = One Product entry in StockLedger.
    
    # Let's fetch the stock ledger entry for this voucher type/id to get product details
    items = models.StockLedger.objects.filter(voucher_type='SALE', voucher_id=sale.id)
    
    # Enrich items with product names
    invoice_items = []
    total_amount = 0
    for item in items:
        prod = models.Products.objects.get(id=item.product_id)
        line_total = item.qty * prod.price
        total_amount += line_total
        invoice_items.append({
            'product_name': prod.product_name,
            'qty': item.qty,
            'price': prod.price,
            'total': line_total
        })
        
    context = {
        'sale': sale,
        'customer': customer,
        'invoice_items': invoice_items,
        'total_amount': total_amount,
        'user_name': request.session.get('name', 'Staff'),
        'user_role': 'STAFF'
    }
    return render(request, 'staffpanel/sales_invoice.html', context)


# Alerts: Stocks & Expiry
def receive_stock_alerts(request):
    check = check_staff_session(request)
    if check:
        return check

    cursor = connection.cursor()
    cursor.execute("""
        SELECT 
            p.id, p.product_name, p.sku, p.reorder_level, p.stock_qty
        FROM products p
        WHERE p.stock_qty <= p.reorder_level
    """)
    alerts = cursor.fetchall()
    
    # Pagination
    paginator = Paginator(alerts, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'alerts': page_obj.object_list,
        'page_obj': page_obj,
        'user_name': request.session.get('name', 'Staff'),
        'user_role': 'STAFF'
    }
    return render(request, 'staffpanel/stock_alerts.html', context)


def send_stock_reminder(request):
    check = check_staff_session(request)
    if check: return check
    
    if request.method == "POST":
        message = request.POST.get('reminder_message', 'Please order the following low-stock items.')
        
        try:
            # Get all low stock items with their unit, using CAST to handle type mismatch between VARCHAR and INT
            cursor = connection.cursor()
            cursor.execute("""
                SELECT p.product_name, p.sku, p.stock_qty, p.reorder_level, 
                       IFNULL(u.unit_name, 'N/A') as unit_name, p.id
                FROM products p
                LEFT JOIN unit u ON CAST(p.unit_id AS UNSIGNED) = u.unit_id
                WHERE p.stock_qty <= p.reorder_level
            """)
            low_stock = cursor.fetchall()
            
            if not low_stock:
                messages.warning(request, "No low stock items found to remind about.")
                return redirect('staff_stock_alerts')
                
            # Format: "Product Name|SKU|Current Qty|Reorder Level|Unit|ProductID" separated by ";"
            summary_list = [f"{item[0]}|{item[1]}|{item[2]}|{item[3]}|{item[4]}|{item[5]}" for item in low_stock]
            summary = "; ".join(summary_list)
            
            # Save reminder
            reminder = models.StockReminder(
                staff_id=request.session.get('user_id'),
                product_list_summary=summary,
                message=message,
                created_at=datetime.datetime.now(),
                is_seen=0
            )
            reminder.save()
            
            messages.success(request, f"Reminder sent to the Manager successfully. ({len(low_stock)} low-stock item(s) included.)")
        except Exception as e:
            messages.error(request, f"Failed to send reminder: {e}")
        
        return redirect('staff_stock_alerts')
    
    return redirect('staff_stock_alerts')



def receive_expiry_alerts(request):
    check = check_staff_session(request)
    if check: return check
    
    return render(request, 'staffpanel/expiry_alerts.html', {'expiring_data': [], 'user_name': request.session.get('name', 'Staff'), 'user_role': 'STAFF'})


# Basic Stock Reports
def view_basic_stock_reports(request):
    check = check_staff_session(request)
    if check:
        return check
        
    cursor = connection.cursor()
    cursor.execute("""
        SELECT 
            p.product_name,
            p.sku,
            u.unit_name,
            p.stock_qty
        FROM products p
        LEFT JOIN unit u ON p.unit_id = u.unit_id
        ORDER BY p.product_name
    """)
    stock_data = cursor.fetchall()
    
    # Handle pagination
    paginator = Paginator(stock_data, 10)  # Show 10 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'stock_report': page_obj.object_list,
        'user_name': request.session.get('name', 'Staff'),
        'user_role': 'STAFF'
    }
    return render(request, 'staffpanel/stock_report.html', context)


def export_stock_report_csv(request):
    check = check_staff_session(request)
    if check:
        return check
        
    cursor = connection.cursor()
    cursor.execute("""
        SELECT 
            p.product_name,
            p.sku,
            u.unit_name,
            p.stock_qty
        FROM products p
        LEFT JOIN unit u ON p.unit_id = u.unit_id
        ORDER BY p.product_name
    """)
    rows = cursor.fetchall()

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="stock_report_{datetime.date.today()}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Product Name', 'SKU', 'Unit', 'Current Stock'])

    for row in rows:
        writer.writerow(row)

    return response


def get_product_stock_ajax(request):
    product_id = request.GET.get('product_id')
    if not product_id:
        return JsonResponse({'stock': 0})
        
    cursor = connection.cursor()
    cursor.execute("SELECT stock_qty FROM products WHERE id = %s", [product_id])
    row = cursor.fetchone()
    stock = row[0] if row and row[0] is not None else 0
    return JsonResponse({'stock': int(stock)})
