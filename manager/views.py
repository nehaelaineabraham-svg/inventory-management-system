from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from inventory import models
from django.db import connection
from django.core.paginator import Paginator
from django.http import HttpResponse
import datetime
import csv
import sys


# Middleware check for manager role
def check_manager_session(request):
    user_type = request.session.get('usertype', '').lower()
    if user_type != 'manager':
        messages.error(request, 'Access denied! Manager login required.')
        return redirect('/login/')
    return None


# Manager Dashboard
def manager_dashboard(request):
    check = check_manager_session(request)
    if check:
        return check
    
    cursor = connection.cursor()
    
    # 1. Basic Counts
    total_products = models.Products.objects.count()
    total_suppliers = models.Suppliers.objects.count()
    total_pos = models.PurchaseOrders.objects.count()
    total_grns = models.Grn.objects.count()
    total_sales = models.Sales.objects.count()
    
    # 2. Recent Purchase Orders (with Supplier Name)
    cursor.execute("""
        SELECT po.id, po.po_date, s.supplier_name, po.status_id
        FROM purchase_orders po
        LEFT JOIN suppliers s ON po.supplier_id = s.id
        ORDER BY po.id DESC
        LIMIT 8
    """)
    recent_pos = cursor.fetchall()
    
    # 3. Low Stock Alerts
    cursor.execute("""
        SELECT 
            p.product_name,
            p.stock_qty as current_stock,
            p.reorder_level
        FROM products p
        WHERE p.stock_qty <= p.reorder_level
        LIMIT 8
    """)
    low_stock_products = cursor.fetchall()
    
    # 4. Total Revenue (from sale_items)
    cursor.execute("SELECT COALESCE(SUM(total), 0) FROM sale_items")
    total_revenue = cursor.fetchone()[0]
    
    # 5. Monthly Revenue (Current Month)
    cursor.execute("""
        SELECT COALESCE(SUM(si.total), 0)
        FROM sale_items si
        JOIN sales s ON si.sale_id = s.id
        WHERE s.sale_date >= DATE_FORMAT(CURRENT_DATE, '%Y-%m-01')
    """)
    monthly_revenue = cursor.fetchone()[0]
    
    # 6. Revenue Trend (Last 7 Days)
    cursor.execute("""
        SELECT s.sale_date, SUM(si.total) as daily_total
        FROM sales s
        JOIN sale_items si ON s.id = si.sale_id
        WHERE s.sale_date >= DATE_SUB(CURRENT_DATE, INTERVAL 7 DAY)
        GROUP BY s.sale_date
        ORDER BY s.sale_date ASC
    """)
    trend_data = cursor.fetchall()
    
    sales_labels = [row[0].strftime('%Y-%m-%d') if hasattr(row[0], 'strftime') else str(row[0]) for row in trend_data]
    sales_data = [float(row[1]) for row in trend_data]
    
    context = {
        'total_products': total_products,
        'total_suppliers': total_suppliers,
        'total_pos': total_pos,
        'total_grns': total_grns,
        'total_sales': total_sales,
        'recent_pos': recent_pos,
        'low_stock_products': low_stock_products,
        'total_revenue': total_revenue,
        'monthly_revenue': monthly_revenue,
        'sales_labels': sales_labels,
        'sales_data': sales_data,
        'user_name': request.session.get('name', 'Manager'),
        'user_role': 'MANAGER'
    }
    return render(request, 'manager/manager_dashboard.html', context)

def manager_change_password(request):
    return render(request, 'manager/change_password.html')

def manager_update_password(request):
    email = request.session.get('semail')
    old_pass = request.POST.get('old_pass')
    new_pass = request.POST.get('new_pass')
    confirm_pass = request.POST.get('confirm_pass')
    
    if new_pass != confirm_pass:
        messages.error(request, 'New password and confirm password do not match!')
        return redirect('manager_change_password')
    
    log_info = models.Login.objects.filter(user_name=email, password=old_pass).first()
    if not log_info:
        messages.error(request, 'Old password is incorrect!')
        return redirect('manager_change_password')
    
    log_info.password = new_pass
    log_info.save()
    
    # Also update the user model if it exists
    user_info = models.Users.objects.filter(email=email).first()
    if user_info:
        user_info.password = new_pass
        user_info.save()
    
    messages.success(request, 'Password updated successfully!')
    return redirect('manager_change_password')

def manager_profile(request):
    check = check_manager_session(request)
    if check:
        return check
    
    email = request.session.get('semail')
    user_details = models.Users.objects.filter(email=email).first()
    
    # Fallback to login info if user_details is missing in Users table
    if not user_details:
        login_info = models.Login.objects.filter(user_name=email).first()
        if login_info:
            # Create a mock object or dictionary that template can use
            user_details = {
                'name': login_info.user_name,
                'email': login_info.user_name,
                'role': login_info.user_type,
                'status': 1 if login_info.user_status.lower() == 'active' else 0,
                'created_at': None
            }
    
    context = {
        'user_details': user_details,
        'user_name': request.session.get('name', 'Manager'),
        'user_role': 'MANAGER'
    }
    return render(request, 'manager/profile.html', context)

def manager_edit_profile(request):
    check = check_manager_session(request)
    if check:
        return check
        
    email = request.session.get('semail')
    user_details = models.Users.objects.filter(email=email).first()
    
    if request.method == 'POST':
        name = request.POST.get('name')
        new_email = request.POST.get('email')
        
        # If user record doesn't exist in Users table, create it
        if not user_details:
            user_details = models.Users(
                role='manager',
                status=1,
                created_at=datetime.datetime.now()
            )
        
        # Update Users model
        user_details.name = name
        user_details.email = new_email
        user_details.save()
        
        # Update Login model if email changed
        if email != new_email:
            login_entry = models.Login.objects.filter(user_name=email).first()
            if login_entry:
                login_entry.user_name = new_email
                login_entry.save()
            request.session['semail'] = new_email
            
        messages.success(request, 'Profile updated successfully!')
        return redirect('manager_profile')
        
    context = {
        'user_details': user_details,
        'user_name': request.session.get('name', 'Manager'),
        'user_role': 'MANAGER'
    }
    return render(request, 'manager/edit_profile.html', context)


# View Products (Read-only)
def view_products(request):
    check = check_manager_session(request)
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
    
    # Paginate (10 per page)
    paginator = Paginator(products_list, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'products': page_obj.object_list,
        'page_obj': page_obj,
        'product_search': product_search,
        'user_name': request.session.get('name', 'Manager'),
        'user_role': 'MANAGER'
    }
    
    if request.GET.get('ajax'):
        return render(request, 'manager/products_table_partial.html', context)
        
    return render(request, 'manager/products_view.html', context)


# View Stock
def view_stock(request):
    check = check_manager_session(request)
    if check:
        return check
    
    cursor = connection.cursor()
    cursor.execute("""
        SELECT 
            p.id,
            p.product_name,
            p.sku,
            p.unit_id,
            u.unit_name,
            COALESCE(stkin.stock_in, 0) as total_in,
            COALESCE(stkout.stock_out, 0) as total_out,
            p.stock_qty as current_stock
        FROM products p
        LEFT JOIN (SELECT product_id, SUM(qty) AS stock_in FROM stock_ledger WHERE in_out = 'IN' GROUP BY product_id) as stkin ON stkin.product_id = p.id
        LEFT JOIN (SELECT product_id, SUM(qty) AS stock_out FROM stock_ledger WHERE in_out = 'OUT' GROUP BY product_id) as stkout ON stkout.product_id = p.id
        LEFT JOIN unit u ON p.unit_id = u.unit_id
        ORDER BY p.product_name
    """)
    stock_list = cursor.fetchall()
    
    # Paginate (8 per page consistent with admin)
    paginator = Paginator(stock_list, 8)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'stock_data': page_obj.object_list,
        'page_obj': page_obj,
        'user_name': request.session.get('name', 'Manager'),
        'user_role': 'MANAGER'
    }
    return render(request, 'manager/stock_view.html', context)


# View Purchase Report
def view_purchase_report(request):
    check = check_manager_session(request)
    if check:
        return check
    
    cursor = connection.cursor()
    cursor.execute("""
        SELECT po.id, po.po_date, s.supplier_name, po.status_id, stat.status, COUNT(gg.id) as grncount, g.total_qty 
        FROM purchase_orders po
        LEFT JOIN suppliers s ON po.supplier_id = s.id
        LEFT JOIN grn gg on po.id = gg.po_id
        LEFT JOIN (SELECT grn_id, SUM(quantity) as total_qty FROM grn_items GROUP BY grn_id) g ON gg.id = g.grn_id
        LEFT JOIN status stat on po.status_id = stat.id
        GROUP BY po.id, po.po_date, s.supplier_name, po.status_id, stat.status
        ORDER BY po.id DESC
    """)
    report_data = cursor.fetchall()
    
    # Paginate (8 per page)
    paginator = Paginator(report_data, 8)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'purchase_data': page_obj.object_list,
        'page_obj': page_obj,
        'user_name': request.session.get('name', 'Manager'),
        'user_role': 'MANAGER'
    }
    return render(request, 'manager/purchase_report.html', context)


# View Sales Report
def view_sales_report(request):
    check = check_manager_session(request)
    if check:
        return check
    
    cursor = connection.cursor()
    cursor.execute("""
        SELECT 
            s.id,
            s.sale_date,
            c.customer_name,
            sl.product_id,
            p.product_name,
            sl.qty
        FROM sales s
        LEFT JOIN customers c ON s.customer_id = c.id
        LEFT JOIN stock_ledger sl ON s.id = sl.voucher_id AND sl.voucher_type = 'SALE'
        LEFT JOIN products p ON sl.product_id = p.id
        ORDER BY s.sale_date DESC
    """)
    sales_list = cursor.fetchall()
    
    # Paginate (8 per page consistent with others)
    paginator = Paginator(sales_list, 8)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'sales_data': page_obj.object_list,
        'page_obj': page_obj,
        'user_name': request.session.get('name', 'Manager'),
        'user_role': 'MANAGER'
    }
    return render(request, 'manager/sales_report.html', context)


# Approve Purchase Orders
def approve_purchase_orders(request):
    check = check_manager_session(request)
    if check:
        return check
    
    # Get all purchase orders with supplier names and totals
    cursor = connection.cursor()
    cursor.execute("""
        SELECT po.id, po.po_date, s.supplier_name, po.status_id, st.status,
               COALESCE(SUM(poi.total_price), 0) as po_total
        FROM purchase_orders po
        LEFT JOIN suppliers s ON po.supplier_id = s.id
        LEFT JOIN purchase_order_items poi ON po.id = poi.po_id
        LEFT JOIN status st ON po.status_id = st.id
        GROUP BY po.id, po.po_date, s.supplier_name, po.status_id, st.status
        ORDER BY po.id DESC
    """)
    pos_raw = cursor.fetchall()
    
    po_data = []
    for po in pos_raw:
        po_data.append({
            'id': po[0],
            'po_date': po[1],
            'supplier_name': po[2],
            'status_id': po[3],
            'status': po[4],
            'po_total': po[5]
        })
    
    # Paginate (10 per page consistent with admin)
    paginator = Paginator(po_data, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'pos': page_obj.object_list,
        'page_obj': page_obj,
        'user_name': request.session.get('name', 'Manager'),
        'user_role': 'MANAGER'
    }
    return render(request, 'manager/approve_po.html', context)


def manager_view_po_items(request, poid):
    check = check_manager_session(request)
    if check: return check

    cursorpo = connection.cursor()
    cursorpo.execute("""
        SELECT pos.id, pos.po_date, pos.supplier_id, st.status
        FROM purchase_orders pos
        LEFT JOIN status st ON pos.status_id = st.id 
        WHERE pos.id = %s
    """, [poid])
    po_raw = cursorpo.fetchall()
    
    if not po_raw:
        messages.error(request, "Purchase Order not found.")
        return redirect('manager_approve_po')

    supplier = get_object_or_404(models.Suppliers, id=po_raw[0][2])

    po = {
        'id': po_raw[0][0],
        'po_date': po_raw[0][1],
        'supplier_id': po_raw[0][2],
        'status': po_raw[0][3] 
    }
    
    cursor = connection.cursor()
    cursor.execute("""
        SELECT poi.id, p.product_name, poi.quantity, poi.unit_price, poi.total_price, u.unit_name
        FROM purchase_order_items poi
        LEFT JOIN products p ON poi.product_id = p.id
        LEFT JOIN unit u ON poi.unit_id = u.unit_id
        WHERE poi.po_id = %s
    """, [poid])
    items_raw = cursor.fetchall()
    
    items = []
    grand_total = 0
    for row in items_raw:
        item = {
            'product_name': row[1],
            'quantity': row[2],
            'unit_price': row[3],
            'total_price': row[4],
            'unit_name': row[5]
        }
        items.append(item)
        grand_total += float(row[4]) if row[4] else 0

    context = {
        'po': [po],  # Wrap in list to match admin template expectations if needed, though dict is cleaner
        'supplier': supplier,
        'items': items,
        'grand_total': grand_total,
        'user_role': 'MANAGER'
    }
    return render(request, 'manager/view_po_items.html', context)


def manager_approve_po_action(request, poid, stat):
    check = check_manager_session(request)
    if check: return check
    
    po = get_object_or_404(models.PurchaseOrders, id=poid)
    po.status_id = stat
    po.save()
    
    status_text = "Approved" if int(stat) == 2 else "Rejected"
    messages.success(request, f"Purchase Order PO-{poid:06d} {status_text} successfully.")
    return redirect('manager_approve_po')


def manager_delete_purchase_order(request, poid):
    check = check_manager_session(request)
    if check: return check
    
    try:
        po = models.PurchaseOrders.objects.get(id=poid)
        if po.status_id == 1: # Only allow deleting pending POs
            po.delete()
            messages.success(request, f"Purchase Order PO-{poid:06d} deleted successfully.")
        else:
            messages.error(request, "Only pending Purchase Orders can be deleted.")
    except Exception as e:
        messages.error(request, f"Error deleting Purchase Order: {str(e)}")
        
    return redirect('manager_approve_po')


# Update PO Status (Approve/Reject)
def update_po_status(request, poid):
    check = check_manager_session(request)
    if check:
        return check
    
    status_str = request.POST.get('status') # 'approved' or 'rejected'
    status_map = {'pending': 1, 'approved': 2, 'rejected': 3}
    status_id = status_map.get(status_str, 1) # Default to 1 (pending) if unknown
    
    po = models.PurchaseOrders.objects.get(id=poid)
    po.status_id = status_id
    po.save()
    
    messages.success(request, f'Purchase Order {poid} updated to {status_str} successfully!')
    return redirect('manager_approve_po')


# Logout
def manager_logout(request):
    request.session.flush()
    messages.success(request, 'Logged out successfully!')
    return redirect('/login/')


# View Categories (Read-only)
def view_categories(request):
    check = check_manager_session(request)
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
        'user_name': request.session.get('name', 'Manager'),
        'user_role': 'MANAGER'
    }
    
    if request.GET.get('ajax'):
        return render(request, 'manager/categories_table_partial.html', context)
        
    return render(request, 'manager/categories_view.html', context)


# Create Purchase Order
def create_purchase_order(request):
    check = check_manager_session(request)
    if check:
        return check
        
    sups = models.Suppliers.objects.all()
    
    # Use raw SQL to join with products and units to get unit_name for product selection
    cursor = connection.cursor()
    cursor.execute("""
        SELECT p.id, p.product_name, p.unit_id, p.price, u.unit_name, p.sku
        FROM products p 
        LEFT JOIN unit u ON p.unit_id = u.unit_id
    """)
    products_raw = cursor.fetchall()
    
    products = [] 
    for row in products_raw:
        products.append({
            'id': row[0],
            'product_name': row[1],
            'unit_id': row[2],
            'price': row[3], 
            'unit_name': row[4],
            'sku': row[5]
        })

    units = models.Units.objects.all()
    
    # Generate PO Number
    last_po = models.PurchaseOrders.objects.latest('id') if models.PurchaseOrders.objects.exists() else None
    next_id = (last_po.id + 1) if last_po else 1
    po_number = f"PO-{next_id:06d}"
    
    # Pre-select product if pid is provided
    preselected_pid = request.GET.get('pid')
    
    context = {
        'suppliers': sups,
        'products': products,
        'units': units,
        'po_number': po_number,
        'preselected_pid': int(preselected_pid) if preselected_pid and preselected_pid.isdigit() else None,
        'user_name': request.session.get('name', 'Manager'),
        'user_role': 'MANAGER'
    }
    return render(request, 'manager/create_purchase_order.html', context)


def save_purchase_order(request):
    check = check_manager_session(request)
    if check:
        return check

    if request.method == "POST":
        supplier_id = request.POST.get("supplier_id")
        po_date = request.POST.get("po_date")
        
        # Save Master PO
        po = models.PurchaseOrders(
            supplier_id=supplier_id,
            po_date=po_date,
            status_id=1,  # 1 = PENDING
            created_at=datetime.datetime.now()
        )
        po.save()
        
        # Save Items
        product_ids = request.POST.getlist('product_id[]')
        quantities = request.POST.getlist('quantity[]')
        prices = request.POST.getlist('price[]')
        units_sent = request.POST.getlist('unit[]')
        
        for i in range(len(product_ids)):
            if product_ids[i]:
                qty = int(quantities[i])
                price = float(prices[i])
                total = qty * price
                u_id = units_sent[i] if i < len(units_sent) else None
                
                models.PurchaseOrderItems.objects.create(
                    po=po,
                    product_id=product_ids[i],
                    quantity=qty,
                    unit_price=price,
                    total_price=total,
                    unit_id=u_id if u_id and u_id != "" and u_id != "None" else None
                )
                
        models.AuditLogs.objects.create(
            user_id=request.session.get('user_id'),
            action='CREATE',
            table_name='purchase_orders',
            record_id=po.id,
            created_at=datetime.datetime.now()
        )
                
        messages.success(request, f'Purchase Order PO-{po.id:06d} created successfully!')
        return redirect('manager_approve_po')
    
    return redirect('manager_approve_po')


# Edit Purchase Order
def edit_purchase_order(request, poid):
    check = check_manager_session(request)
    if check: return check
        
    po = get_object_or_404(models.PurchaseOrders, id=poid)
    postatus = get_object_or_404(models.DocStatus, id=po.status_id)
    has_grn = models.Grn.objects.filter(po_id=poid).exists()

    sups = models.Suppliers.objects.all()
    cursor = connection.cursor()

    # Fetch Purchase Order Items with Unit and Product Names
    cursor.execute("""
        SELECT poi.id, poi.product_id, poi.quantity, poi.unit_price, poi.total_price, 
               poi.unit_id, u.unit_name, p.product_name
        FROM purchase_order_items poi
        LEFT JOIN unit u ON poi.unit_id = u.unit_id
        LEFT JOIN products p ON poi.product_id = p.id
        WHERE poi.po_id = %s
    """, [poid])
    items_raw = cursor.fetchall()
    
    items = []
    for row in items_raw:
        items.append({
            'id': row[0],
            'product_id': row[1],
            'quantity': row[2],
            'unit_price': row[3],
            'total_price': row[4],
            'unit_id': row[5],
            'unit_name': row[6],
            'product_name': row[7]
        })

    # Fetch all products for the dropdown
    cursor.execute("""
        SELECT p.id, p.product_name, p.unit_id, p.price, u.unit_name, p.sku
        FROM products p 
        LEFT JOIN unit u ON p.unit_id = u.unit_id
    """)
    products_raw = cursor.fetchall()
    
    products = [] 
    for row in products_raw:
        products.append({
            'id': row[0],
            'product_name': row[1],
            'unit_id': row[2],
            'price': row[3], 
            'unit_name': row[4],
            'sku': row[5]
        })

    units = models.Units.objects.all()

    context = {
        "po": po,
        "suppliers": sups,
        "items": items,
        "products": products,
        "units": units,
        "has_grn": has_grn,
        "status": postatus,
        'user_name': request.session.get('name', 'Manager'),
        'user_role': 'MANAGER'
    }
    return render(request, 'manager/edit_purchase_order.html', context)


def update_purchase_order(request):
    check = check_manager_session(request)
    if check: return check

    if request.method == "POST":
        poid = request.POST.get('poid')
        po = get_object_or_404(models.PurchaseOrders, id=poid)

        if models.Grn.objects.filter(po_id=poid).exists():
            messages.error(request, "Update not allowed. GRN already exists for this PO.")
            return redirect('manager_approve_po')

        po.supplier_id = request.POST.get('supplier_id')
        po.po_date = request.POST.get('po_date')
        po.save()

        # DELETE OLD ITEMS
        models.PurchaseOrderItems.objects.filter(po_id=poid).delete()

        # GET NEW ITEMS
        product_ids = request.POST.getlist('product_id[]')
        quantities = request.POST.getlist('quantity[]')
        unit_prices = request.POST.getlist('unit_price[]')
        units_sent = request.POST.getlist('unit[]')

        grand_total = 0
        for i in range(len(product_ids)):
            if product_ids[i] != "":
                try:
                    quantity = int(quantities[i])
                    price = float(unit_prices[i])
                    total = quantity * price
                    u_id = units_sent[i] if i < len(units_sent) else None

                    models.PurchaseOrderItems.objects.create(
                        po_id=poid,
                        product_id=product_ids[i],
                        quantity=quantity,
                        unit_price=price,
                        total_price=total,
                        unit_id=u_id if u_id and u_id != 'None' else None
                    )
                    grand_total += total
                except (ValueError, TypeError):
                    continue

        # Log activity directly to avoid import issues
        models.AuditLogs.objects.create(
            user_id=request.session.get('user_id'),
            action='UPDATE',
            table_name='purchase_orders',
            record_id=poid,
            created_at=datetime.datetime.now()
        )

        messages.success(request, f"Purchase Order PO-{int(poid):06d} Updated Successfully!")
        return redirect('manager_approve_po')

    return redirect('manager_approve_po')


# Track Purchase Order Status (View Details)
def track_purchase_order_status(request, poid):
    check = check_manager_session(request)
    if check:
        return check
        
    # Get Master PO Details
    po = models.PurchaseOrders.objects.get(id=poid)
    supplier = models.Suppliers.objects.get(id=po.supplier_id)
    
    # Get PO Items
    cursor = connection.cursor()
    cursor.execute("""
        SELECT poi.id, p.product_name, poi.quantity, poi.unit_price, poi.total_price
        FROM purchase_order_items poi
        LEFT JOIN products p ON poi.product_id = p.id
        WHERE poi.po_id = %s
    """, [poid])
    items = cursor.fetchall()
    
    context = {
        "po": po,
        "supplier": supplier,
        "items": items,
        'user_name': request.session.get('name', 'Manager'),
        'user_role': 'MANAGER'
    }
    return render(request, 'manager/track_po_status.html', context)


# Review Supplier Performance
def review_supplier_performance(request):
    check = check_manager_session(request)
    if check:
        return check
        
    cursor = connection.cursor()
    cursor.execute("""
        SELECT 
            s.id,
            s.supplier_name,
            COUNT(DISTINCT po.id) as total_pos,
            COUNT(DISTINCT CASE WHEN po.status_id IN (2, 4) THEN po.id END) as approved_pos,
            COUNT(DISTINCT CASE WHEN po.status_id = 1 THEN po.id END) as pending_pos
        FROM suppliers s
        LEFT JOIN purchase_orders po ON s.id = po.supplier_id
        GROUP BY s.id, s.supplier_name
        ORDER BY total_pos DESC
    """)
    performance_list = cursor.fetchall()
    
    # Paginate (8 per page consistent with others)
    paginator = Paginator(performance_list, 8)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'performance_data': page_obj.object_list,
        'page_obj': page_obj,
        'user_name': request.session.get('name', 'Manager'),
        'user_role': 'MANAGER'
    }
    return render(request, 'manager/supplier_performance.html', context)


# View Customer Sales Trends
def view_customer_sales_trends(request):
    check = check_manager_session(request)
    if check:
        return check

    cursor = connection.cursor()
    cursor.execute("""
        SELECT 
            c.id,
            c.customer_name,
            COUNT(s.id) as total_sales,
            MAX(s.sale_date) as last_sale_date
        FROM customers c
        LEFT JOIN sales s ON c.id = s.customer_id
        GROUP BY c.id, c.customer_name
        ORDER BY total_sales DESC
    """)
    trends_list = cursor.fetchall()
    
    # Paginate (8 per page consistent with others)
    paginator = Paginator(trends_list, 8)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'trends_data': page_obj.object_list,
        'page_obj': page_obj,
        'user_name': request.session.get('name', 'Manager'),
        'user_role': 'MANAGER'
    }
    return render(request, 'manager/customer_trends.html', context)


# CSV Exports
def purchase_report_csv(request):
    check = check_manager_session(request)
    if check: return check
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="purchase_report.csv"'
    writer = csv.writer(response)
    writer.writerow(['PO ID', 'Date', 'Supplier', 'Status', 'GRN Count', 'Total Qty'])
    cursor = connection.cursor()
    cursor.execute("""
        SELECT CONCAT('PO-',  RIGHT(CONCAT('0000000', po.id), 6)) as v, po.po_date, s.supplier_name, stat.status, COUNT(gg.id) as grncount, IFNULL(g.total_qty, 0) AS total_qty
        FROM purchase_orders po
        LEFT JOIN suppliers s ON po.supplier_id = s.id
        LEFT JOIN grn gg on po.id = gg.po_id
        LEFT JOIN (SELECT grn_id, sum(quantity) as total_qty from grn_items group by grn_id) g ON gg.id = g.grn_id
        LEFT JOIN status stat on po.status_id = stat.id
        GROUP BY po.id, po.po_date, s.supplier_name, po.status_id
        ORDER BY po.id
    """)
    for row in cursor.fetchall(): writer.writerow(row)
    return response


def sales_report_csv(request):
    check = check_manager_session(request)
    if check: return check

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sales_report.csv"'
    writer = csv.writer(response)
    writer.writerow(['Sale ID', 'Date', 'Customer', 'Sales Value'])
    cursor = connection.cursor()
    for row in cursor.fetchall(): writer.writerow(row)
    return response


def supplier_performance_csv(request):
    check = check_manager_session(request)
    if check: return check

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="supplier_performance.csv"'
    writer = csv.writer(response)
    writer.writerow(['Supplier Name', 'Total POs', 'Approved POs', 'Pending POs', 'Performance Rating'])
    
    cursor = connection.cursor()
    cursor.execute("""
        SELECT 
            s.supplier_name,
            COUNT(DISTINCT po.id) as total_pos,
            COUNT(DISTINCT CASE WHEN po.status_id IN (2, 4) THEN po.id END) as approved_pos,
            COUNT(DISTINCT CASE WHEN po.status_id = 1 THEN po.id END) as pending_pos
        FROM suppliers s
        LEFT JOIN purchase_orders po ON s.id = po.supplier_id
        GROUP BY s.id, s.supplier_name
        ORDER BY total_pos DESC
    """)
    
    for row in cursor.fetchall():
        supplier_name = row[0]
        total_pos = row[1]
        approved_pos = row[2]
        pending_pos = row[3]
        
        rating = "-"
        if approved_pos > 0:
            percentage = (approved_pos / total_pos) * 100
            if percentage >= 90: rating = "Excellent"
            elif percentage >= 75: rating = "Good"
            elif percentage >= 50: rating = "Average"
            else: rating = "Poor"
            
        writer.writerow([supplier_name, total_pos, approved_pos, pending_pos, rating])
        
    return response


# View Purchase Analytics
def view_purchase_analytics(request):
    check = check_manager_session(request)
    if check:
        return check
        
    cursor = connection.cursor()
    cursor.execute("""
        SELECT 
            p.product_name,
            SUM(poi.quantity) as total_qty,
            SUM(poi.total_price) as total_spend
        FROM purchase_order_items poi
        JOIN products p ON poi.product_id = p.id
        JOIN purchase_orders po ON poi.po_id = po.id
        WHERE po.status_id IN (2, 4)
        GROUP BY p.product_name
        ORDER BY total_spend DESC
    """)
    analytics_list = cursor.fetchall()
    
    # Paginate (8 per page consistent with others)
    paginator = Paginator(analytics_list, 8)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'analytics_data': page_obj.object_list,
        'page_obj': page_obj,
        'user_name': request.session.get('name', 'Manager'),
        'user_role': 'MANAGER'
    }
    return render(request, 'manager/purchase_analytics.html', context)


def purchase_analytics_csv(request):
    check = check_manager_session(request)
    if check: return check

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="purchase_analytics.csv"'
    writer = csv.writer(response)
    writer.writerow(['Product Name', 'Total Quantity Purchased', 'Total Spend'])
    
    cursor = connection.cursor()
    cursor.execute("""
        SELECT 
            p.product_name,
            SUM(poi.quantity) as total_qty,
            SUM(poi.total_price) as total_spend
        FROM purchase_order_items poi
        JOIN products p ON poi.product_id = p.id
        JOIN purchase_orders po ON poi.po_id = po.id
        WHERE po.status_id IN (2, 4)
        GROUP BY p.product_name
        ORDER BY total_spend DESC
    """)
    
    for row in cursor.fetchall():
        writer.writerow(row)
        
    return response


# View Stock Trends (Simplification: Current Stock vs Reorder Level)
def view_stock_trends(request):
    # This is similar to alerts but visualized as trends/status_id
    return redirect('manager_stock') # Reuse stock view for now or create specific trend view


# Alerts & Notifications
def view_alerts(request):
    check = check_manager_session(request)
    if check:
        return check
        
    # Get low stock items
    cursor = connection.cursor()
    cursor.execute("""
        SELECT 
            p.id, p.product_name, p.sku, p.reorder_level,
            p.stock_qty as current_stock
        FROM products p
        WHERE p.stock_qty <= p.reorder_level
    """)
    low_stock_list = cursor.fetchall()
    
    # Paginate (8 per page consistent with others)
    paginator = Paginator(low_stock_list, 8)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'low_stock_items': page_obj.object_list,
        'page_obj': page_obj,
        'user_name': request.session.get('name', 'Manager'),
        'user_role': 'MANAGER'
    }
    return render(request, 'manager/alerts.html', context)


def alerts_csv(request):
    check = check_manager_session(request)
    if check: return check

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="low_stock_alerts.csv"'
    writer = csv.writer(response)
    writer.writerow(['Product Name', 'SKU', 'Reorder Level', 'Current Stock'])
    
    cursor = connection.cursor()
    cursor.execute("""
        SELECT 
            p.product_name, p.sku, p.reorder_level,
            p.stock_qty as current_stock
        FROM products p
        WHERE p.stock_qty <= p.reorder_level
    """)
    
    for row in cursor.fetchall():
        writer.writerow(row)
        
    return response


# Audit & Activity Log (Manager View)
def view_related_activity_logs(request):
    check = check_manager_session(request)
    if check:
        return check
        
    # Show logs related to purchasing and sales or initiated by this manager
    user_id = request.session.get('user_id')
    
    logs_list = models.AuditLogs.objects.filter(user_id=user_id).order_by('-created_at')
    
    # Paginate (8 per page consistent with others)
    paginator = Paginator(logs_list, 8)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'logs': page_obj.object_list,
        'page_obj': page_obj,
        'user_name': request.session.get('name', 'Manager'),
        'user_role': 'MANAGER'
    }
    return render(request, 'manager/activity_logs.html', context)

# Approve GRN
def manager_approve_grn(request):
    check = check_manager_session(request)
    if check: return check
    
    cursor = connection.cursor()
    cursor.execute("""
        SELECT 
            g.id, 
            g.grn_date, 
            po.id as po_id, 
            po.po_date, 
            s.supplier_name, 
            COALESCE(SUM(gi.grn_amount), 0) as total_amount,
            g.status_id,
            st.status
        FROM grn g
        LEFT JOIN purchase_orders po ON g.po_id = po.id
        LEFT JOIN suppliers s ON po.supplier_id = s.id
        LEFT JOIN grn_items gi ON g.id = gi.grn_id
        LEFT JOIN status st ON g.status_id = st.id
        WHERE g.status_id = 1  -- Show only Pending
        GROUP BY g.id, g.grn_date, po.id, po.po_date, s.supplier_name, g.status_id, st.status
        ORDER BY g.id DESC
    """)
    grns_raw = cursor.fetchall()
    
    # Paginate
    paginator = Paginator(grns_raw, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'grns': page_obj.object_list,
        'page_obj': page_obj,
        'user_name': request.session.get('name', 'Manager'),
        'user_role': 'MANAGER'
    }
    return render(request, 'manager/approve_grn.html', context)


def manager_approve_grn_action(request, gid, stat):
    check = check_manager_session(request)
    if check: return check
    
    try:
        grn = models.Grn.objects.get(id=gid)
        if grn.status_id != 1: # Only Pending can be acted upon
            messages.warning(request, 'GRN is not in pending status.')
            return redirect('manager_approve_grn')

        # Update Status (2=Approved, 3=Rejected)
        grn.status_id = stat
        grn.save()
        
        status_text = "Approved" if int(stat) == 2 else "Rejected"
        
        if int(stat) == 2: # If Approved, update stock
            grn_items = models.GRNItems.objects.filter(grn_id=grn.id)
            for item in grn_items:
                prod = models.Products.objects.get(id=item.product_id)
                prod.stock_qty = (prod.stock_qty or 0) + int(item.quantity or 0)
                prod.save()
                
                # Create Ledger Entry
                models.StockLedger.objects.create(
                    product_id=item.product_id,
                    voucher_type='GRN',
                    voucher_id=grn.id,
                    qty=item.quantity,
                    in_out='IN',
                    created_at=datetime.datetime.now()
                )
            messages.success(request, f'GRN-{gid:06d} Approved and Stock Updated successfully.')
        else:
            messages.success(request, f'GRN-{gid:06d} Rejected successfully.')
            
    except models.Grn.DoesNotExist:
        messages.error(request, 'GRN not found.')
        
    return redirect('manager_approve_grn')


def manager_view_grn_items(request, gid):
    check = check_manager_session(request)
    if check: return check
    
    cursor = connection.cursor()
    # Fetch GRN Master Details
    cursor.execute("""
        SELECT g.id, g.grn_date, g.po_id, po.po_date, s.supplier_name, st.status
        FROM grn g
        LEFT JOIN purchase_orders po ON g.po_id = po.id
        LEFT JOIN suppliers s ON po.supplier_id = s.id
        LEFT JOIN status st ON g.status_id = st.id
        WHERE g.id = %s
    """, [gid])
    grn_raw = cursor.fetchone()
    
    if not grn_raw:
        messages.error(request, "GRN not found.")
        return redirect('manager_approve_grn')
        
    grn_details = {
        'id': grn_raw[0],
        'grn_date': grn_raw[1],
        'po_id': grn_raw[2],
        'po_date': grn_raw[3],
        'supplier_name': grn_raw[4],
        'status': grn_raw[5]
    }
    
    # Fetch GRN Items
    cursor.execute("""
        SELECT gi.id, p.product_name, gi.po_qty, gi.bal_qty, gi.quantity, gi.rate, gi.grn_amount, u.unit_name
        FROM grn_items gi
        LEFT JOIN products p ON gi.product_id = p.id
        LEFT JOIN unit u ON gi.unit_id = u.unit_id
        WHERE gi.grn_id = %s
    """, [gid])
    items_raw = cursor.fetchall()
    
    items = []
    grand_total = 0
    for row in items_raw:
        items.append({
            'product_name': row[1],
            'po_qty': row[2],
            'bal_qty': row[3],
            'quantity': row[4],
            'rate': row[5],
            'total': row[6],
            'unit_name': row[7]
        })
        grand_total += float(row[6]) if row[6] else 0
        
    context = {
        'grn': grn_details,
        'items': items,
        'grand_total': grand_total,
        'user_name': request.session.get('name', 'Manager'),
        'user_role': 'MANAGER'
    }
    return render(request, 'manager/view_grn_items.html', context)


# Approve Stock Adjustments
def manager_approve_adjustments(request):
    check = check_manager_session(request)
    if check: return check
    
    cursor = connection.cursor()
    cursor.execute("""
        SELECT 
            sa.id, 
            sa.created_at, 
            p.product_name, 
            sa.qty, 
            sa.action_type, 
            u.name as staff_name,
            st.status,
            sa.status_id,
            sa.reason
        FROM stock_adjustments sa
        LEFT JOIN products p ON sa.product_id = p.id
        LEFT JOIN users u ON sa.created_by = u.id
        LEFT JOIN status st ON sa.status_id = st.id
        WHERE sa.status_id = 1
        ORDER BY sa.id DESC
    """)
    adjustments_raw = cursor.fetchall()
    
    # Paginate
    paginator = Paginator(adjustments_raw, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'adjustments': page_obj.object_list,
        'page_obj': page_obj,
        'user_name': request.session.get('name', 'Manager'),
        'user_role': 'MANAGER'
    }
    return render(request, 'manager/approve_adjustments.html', context)


# View Stock Adjustment Details
def manager_view_adjustment_details(request, aid):
    check = check_manager_session(request)
    if check: return check
    
    cursor = connection.cursor()
    cursor.execute("""
        SELECT 
            sa.id, 
            sa.created_at, 
            p.product_name, 
            p.sku,
            sa.qty, 
            sa.action_type, 
            u.name as staff_name,
            st.status,
            sa.reason,
            p.stock_qty as current_stock,
            unt.unit_name
        FROM stock_adjustments sa
        LEFT JOIN products p ON sa.product_id = p.id
        LEFT JOIN users u ON sa.created_by = u.id
        LEFT JOIN status st ON sa.status_id = st.id
        LEFT JOIN unit unt ON sa.unit_id = unt.unit_id
        WHERE sa.id = %s
    """, [aid])
    adj_raw = cursor.fetchone()
    
    if not adj_raw:
        messages.error(request, 'Adjustment record not found.')
        return redirect('manager_approve_adjustments')
        
    adjustment = {
        'id': adj_raw[0],
        'date': adj_raw[1],
        'product_name': adj_raw[2],
        'sku': adj_raw[3],
        'qty': adj_raw[4],
        'type': adj_raw[5],
        'staff': adj_raw[6],
        'status': adj_raw[7],
        'reason': adj_raw[8],
        'current_stock': adj_raw[9],
        'unit_name': adj_raw[10]
    }
    
    context = {
        'adj': adjustment,
        'user_name': request.session.get('name', 'Manager'),
        'user_role': 'MANAGER'
    }
    return render(request, 'manager/view_adjustment.html', context)


def manager_approve_adjustment_action(request, aid, stat):
    check = check_manager_session(request)
    if check: return check
    
    try:
        adj = models.StockAdjustment.objects.get(id=aid)
        if adj.status_id != 1:
            messages.warning(request, 'Adjustment is not in pending status.')
            return redirect('manager_approve_adjustments')

        adj.status_id = stat
        adj.save()
        
        if int(stat) == 2: # Approved
            prod = models.Products.objects.get(id=adj.product_id)
            in_out = 'IN' if adj.action_type == 'ADD' else 'OUT'
            
            # Update product stock_qty
            if in_out == 'IN':
                prod.stock_qty = (prod.stock_qty or 0) + adj.qty
            else:
                prod.stock_qty = (prod.stock_qty or 0) - adj.qty
            prod.save()
            
            # Create Ledger Entry
            models.StockLedger.objects.create(
                product_id=adj.product_id,
                voucher_type='ADJUSTMENT',
                voucher_id=adj.id,
                qty=adj.qty,
                unit_id=adj.unit_id,
                in_out=in_out,
                created_at=datetime.datetime.now()
            )
            messages.success(request, f'Adjustment ADJ-{aid:06d} Approved and Stock Updated.')
        else:
            messages.success(request, f'Adjustment ADJ-{aid:06d} Rejected.')
            
    except models.StockAdjustment.DoesNotExist:
        messages.error(request, 'Adjustment not found.')
        
    return redirect('manager_approve_adjustments')


def view_stock_reminders(request):
    check = check_manager_session(request)
    if check: return check
    
    # Get reminders with staff names
    cursor = connection.cursor()
    cursor.execute("""
        SELECT sr.id, sr.product_list_summary, sr.message, sr.created_at, sr.is_seen, u.name
        FROM stock_reminders sr
        LEFT JOIN users u ON sr.staff_id = u.id
        ORDER BY sr.created_at DESC
    """)
    reminders_raw = cursor.fetchall()
    
    # Process into list of dicts
    reminders = []
    for r in reminders_raw:
        reminders.append({
            'id': r[0],
            'summary': r[1],
            'message': r[2],
            'date': r[3],
            'is_seen': r[4],
            'staff_name': r[5] or 'Unknown Staff'
        })
    
    context = {
        'reminders': reminders,
        'user_name': request.session.get('name', 'Manager'),
        'user_role': 'MANAGER'
    }
    return render(request, 'manager/stock_reminders.html', context)


def mark_reminder_seen(request, rid):
    check = check_manager_session(request)
    if check: return check
    
    try:
        reminder = models.StockReminder.objects.get(id=rid)
        reminder.is_seen = 1
        reminder.save()
        messages.success(request, "Reminder marked as seen.")
    except models.StockReminder.DoesNotExist:
        messages.error(request, "Reminder not found.")
        
    return redirect('manager_stock_reminders')


def reminder_detail(request, rid):
    check = check_manager_session(request)
    if check: return check
    
    try:
        # Get specific reminder with staff name
        cursor = connection.cursor()
        cursor.execute("""
            SELECT sr.id, sr.product_list_summary, sr.message, sr.created_at, sr.is_seen, u.name
            FROM stock_reminders sr
            LEFT JOIN users u ON sr.staff_id = u.id
            WHERE sr.id = %s
        """, [rid])
        r = cursor.fetchone()
        
        if not r:
            messages.error(request, "Reminder not found.")
            return redirect('manager_stock_reminders')
            
        # Parse structured summary for table view
        items = []
        summary_raw = r[1] or ""
        if "|" in summary_raw:
            # Format: "Name|SKU|Qty|Reorder|Unit|ProductID"
            batches = summary_raw.split(";")
            for batch in batches:
                parts = batch.strip().split("|")
                if len(parts) >= 4:
                    items.append({
                        'name': parts[0],
                        'sku': parts[1],
                        'qty_at_reminder': parts[2],  # Stock level when reminder was sent
                        'qty': parts[2],              # Will be replaced with live stock
                        'reorder': parts[3],
                        'unit': parts[4] if len(parts) >= 5 else 'N/A',
                        'product_id': parts[5].strip() if len(parts) >= 6 else None,
                        'fulfilled': False
                    })
        elif summary_raw:
            # Fallback for old formats
            import re
            batches = summary_raw.split(",")
            for batch in batches:
                batch = batch.strip()
                if not batch: continue
                match = re.search(r"(.*) \(Current: ([\d\.]+)\)", batch)
                if match:
                    items.append({
                        'name': match.group(1),
                        'sku': 'N/A',
                        'qty_at_reminder': match.group(2),
                        'qty': match.group(2),
                        'reorder': 'N/A',
                        'unit': 'N/A',
                        'product_id': None,
                        'fulfilled': False
                    })
                else:
                    items.append({
                        'name': batch,
                        'sku': 'N/A',
                        'qty_at_reminder': 'N/A',
                        'qty': 'N/A',
                        'reorder': 'N/A',
                        'unit': 'N/A',
                        'product_id': None,
                        'fulfilled': False
                    })
        
        # --- Fetch LIVE stock values for each item with a known product_id ---
        product_ids = [item['product_id'] for item in items if item.get('product_id') and str(item['product_id']).isdigit()]
        if product_ids:
            placeholders = ','.join(['%s'] * len(product_ids))
            cursor.execute(f"""
                SELECT p.id, p.stock_qty, p.reorder_level, IFNULL(u.unit_name, 'N/A')
                FROM products p
                LEFT JOIN unit u ON CAST(p.unit_id AS UNSIGNED) = u.unit_id
                WHERE p.id IN ({placeholders})
            """, product_ids)
            live_stock_rows = cursor.fetchall()
            # Build a lookup: {product_id: (live_qty, live_reorder, live_unit)}
            live_lookup = {str(row[0]): (row[1], row[2], row[3]) for row in live_stock_rows}
            
            # Update each item with live values
            for item in items:
                pid = str(item.get('product_id', ''))
                if pid in live_lookup:
                    live_qty, live_reorder, live_unit = live_lookup[pid]
                    item['qty'] = live_qty
                    item['reorder'] = live_reorder
                    if live_unit and live_unit != 'N/A':
                        item['unit'] = live_unit
                    # Mark as fulfilled if stock is now above reorder level
                    try:
                        item['fulfilled'] = int(live_qty) > int(live_reorder)
                    except (ValueError, TypeError):
                        item['fulfilled'] = False
        
        reminder = {
            'id': r[0],
            'summary': r[1],
            'items': items,
            'message': r[2],
            'date': r[3],
            'is_seen': r[4],
            'staff_name': r[5] or 'Unknown Staff'
        }
        
    except Exception as e:
        messages.error(request, f"Error fetching reminder: {e}")
        return redirect('manager_stock_reminders')
    
    context = {
        'r': reminder,
        'user_name': request.session.get('name', 'Manager'),
        'user_role': 'MANAGER'
    }
    return render(request, 'manager/reminder_detail.html', context)
