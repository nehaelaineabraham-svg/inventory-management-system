from django.shortcuts import get_object_or_404, render, redirect
from inventory import models
from django.contrib import messages
import datetime
from django.utils import timezone
from datetime import datetime as dt, timedelta
from django.db.models import Sum, Count, F
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.db import connection
from django.core.paginator import Paginator
import csv

# Middleware check for admin role
def check_admin_session(request):
    user_type = request.session.get('usertype', '').lower()
    if user_type != 'admin':
        messages.error(request, 'Access denied! Admin login required.')
        return redirect('/')
    return None

def log_activity(request, action, table_name=None, record_id=None):
    user_id = request.session.get('user_id')
    # If user_id is not in session (e.g. if not set in login), try to find by email
    if not user_id:
        email = request.session.get('semail')
        if email:
            u = models.Login.objects.filter(user_name=email).first()
            if u:
                user_id = u.user_id
    
    if user_id:
        final_action = action
        final_record_id = None
        
        # Safe handling of record_id which is a BigIntegerField
        if isinstance(record_id, (int, float)):
            final_record_id = int(record_id)
        elif isinstance(record_id, str) and record_id.isdigit():
            final_record_id = int(record_id)
        elif record_id:
            # If record_id is a string description, append to action instead of crashing
            final_action = f"{action}: {record_id}"

        models.AuditLogs.objects.create(
            user_id=user_id,
            action=final_action,
            table_name=table_name,
            record_id=final_record_id,
            created_at=dt.now()
        )
def admin_dashboard(request):

    today = dt.now().date()
    this_month = today.month
    this_year = today.year

    # =========================
    # BASIC COUNTS
    # =========================
    total_users = models.Users.objects.filter(status=1).count()
    total_products = models.Products.objects.count()
    total_sales = models.Sales.objects.count()
    total_grns = models.Grn.objects.count()
    total_suppliers = models.Suppliers.objects.count()
    total_pos = models.PurchaseOrders.objects.count()

    # =========================
    # TOTAL REVENUE
    # =========================
    total_revenue = models.SaleItems.objects.aggregate(
        total=Sum('total')
    )['total'] or 0

    # =========================
    # TODAY REVENUE
    # =========================
    today_sales_ids = models.Sales.objects.filter(
        sale_date=today
    ).values_list('id', flat=True)

    today_revenue = models.SaleItems.objects.filter(
        sale_id__in=today_sales_ids
    ).aggregate(total=Sum('total'))['total'] or 0

    # =========================
    # MONTHLY REVENUE
    # =========================
    monthly_sales_ids = models.Sales.objects.filter(
        sale_date__month=this_month,
        sale_date__year=this_year
    ).values_list('id', flat=True)

    monthly_revenue = models.SaleItems.objects.filter(
        sale_id__in=monthly_sales_ids
    ).aggregate(total=Sum('total'))['total'] or 0

    # =========================
    # LAST MONTH GROWTH
    # =========================
    if this_month == 1:
        last_month = 12
        last_year = this_year - 1
    else:
        last_month = this_month - 1
        last_year = this_year

    last_month_sales_ids = models.Sales.objects.filter(
        sale_date__month=last_month,
        sale_date__year=last_year
    ).values_list('id', flat=True)

    last_month_revenue = models.SaleItems.objects.filter(
        sale_id__in=last_month_sales_ids
    ).aggregate(total=Sum('total'))['total'] or 0

    if last_month_revenue > 0:
        growth = ((monthly_revenue - last_month_revenue) / last_month_revenue) * 100
    else:
        growth = 0

    # =========================
    # LOW STOCK PRODUCTS (Dynamic Calculation)
    # =========================
    cursor = connection.cursor()
    cursor.execute("""
        SELECT 
            p.id,
            p.product_name,
            p.sku,
            p.reorder_level,
            p.stock_qty
        FROM products p
        WHERE p.stock_qty <= p.reorder_level
        ORDER BY p.stock_qty ASC
    """)
    low_stock_raw = cursor.fetchall()
    
    low_stock_products = []
    for row in low_stock_raw:
        low_stock_products.append({
            'product_name': row[1],
            'sku': row[2],
            'reorder_level': row[3],
            'stock_qty': row[4]
        })

    low_stock_count = len(low_stock_products)


    # =========================
    # LAST 7 DAYS GRAPH
    # =========================
    sales_labels = []
    sales_data = []

    for i in range(6, -1, -1):
        day = today - timedelta(days=i)

        day_sales_ids = models.Sales.objects.filter(
            sale_date=day
        ).values_list('id', flat=True)

        day_total = models.SaleItems.objects.filter(
            sale_id__in=day_sales_ids
        ).aggregate(total=Sum('total'))['total'] or 0

        sales_labels.append(day.strftime("%d %b"))
        sales_data.append(float(day_total))

    # =========================
    # RECENT SALES
    # =========================
    recent_sales = models.Sales.objects.order_by('-sale_date')[:5]

    # =========================
    # CONTEXT
    # =========================
    context = {
        'total_users': total_users,
        'total_products': total_products,
        'total_sales': total_sales,
        'total_grns': total_grns,
        'total_suppliers': total_suppliers,
        'total_pos': total_pos,
        'total_revenue': total_revenue,
        'today_revenue': today_revenue,
        'monthly_revenue': monthly_revenue,
        'growth': round(growth, 2),
        'low_stock_products': low_stock_products,
        'low_stock_count': low_stock_count,
        'sales_labels': sales_labels,
        'sales_data': sales_data,
        'recent_sales': recent_sales,
    }

    return render(request, 'admin/admin.html', context)


# Users CRUD
def users(request):
    users_list = models.Users.objects.all().order_by('id')
    
    # Paginate the users (10 per page)
    paginator = Paginator(users_list, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'users': page_obj.object_list,
        'page_obj': page_obj
    }
    return render(request, 'users/users.html', context)

def save_user(request):
    name = request.POST["name"]
    email = request.POST["email"]
    role = request.POST["role"]
    password = request.POST["password"]
    
    # Check if email exists
    existing_user = models.Users.objects.filter(email=email).first()
    if existing_user:
        messages.success(request, 'Email already exists!!!!!')
        return redirect('users')
    
    # Save user
    sdata = models.Users(
        name=name,
        email=email,
        role=role,
        password=password,
        status=1
    )
    sdata.save()
    
    # Create login entry
    log = models.Login(
        user_name=email,
        password=password,
        user_type=role,
        user_status='active'
    )
    log.save()
    
    log_activity(request, 'CREATE', 'users', sdata.id)
    
    messages.success(request, 'User created successfully!')
    return redirect(users)

def edit_user(request, uid):
    sdata = models.Users.objects.get(id=uid)
    context = {
        "user": sdata
    }
    return render(request, 'users/users_edit.html', context)

def update_user(request):
    uid = request.POST['uid']
    name = request.POST['name']
    email = request.POST['email']
    role = request.POST['role']
    password = request.POST.get('password')
    
    sdata = models.Users.objects.get(id=uid)
    sdata.name = name
    sdata.email = email
    sdata.role = role
    if password:
        sdata.password = password
    sdata.save()
    
    log_activity(request, 'UPDATE', 'users', uid)
    
    messages.success(request, 'Updated successfully!')
    return redirect(users)

def delete_user(request, uid):
    sdata = models.Users.objects.get(id=uid)
    
    # Delete login entry
    log_info = models.Login.objects.filter(user_name=sdata.email)
    log_info.delete()
    
    sdata.delete()
    log_activity(request, 'DELETE', 'users', uid)
    messages.success(request, 'Deleted successfully!!!!')
    return redirect(users)

def activate_user(request, uid):
    sdata = models.Users.objects.get(id=uid)
    sdata.status = 1
    sdata.save()
    
    # Update Login status
    log = models.Login.objects.filter(user_name=sdata.email).first()
    if log:
        log.user_status = 'active'
        log.save()
        
    log_activity(request, 'ACTIVATE', 'users', uid)
    
    messages.success(request, 'User activated successfully!')
    return redirect(users)

def deactivate_user(request, uid):
    sdata = models.Users.objects.get(id=uid)
    sdata.status = 0
    sdata.save()
    
    # Update Login status
    log = models.Login.objects.filter(user_name=sdata.email).first()
    if log:
        log.user_status = 'inactive'
        log.save()
        
    log_activity(request, 'DEACTIVATE', 'users', uid)
    
    messages.success(request, 'User deactivated successfully!')
    return redirect(users)

def user_activity_logs(request):
    logs_list = models.AuditLogs.objects.all().order_by('-created_at')
    
    # Paginate the logs (20 per page)
    paginator = Paginator(logs_list, 6)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'logs': page_obj.object_list,
        'page_obj': page_obj
    }
    return render(request, 'users/user_logs.html', context)

# Password Change
def change_password(request):
    return render(request, 'admin/change_password.html')
def update_pass_admin(request):
    email = request.session.get('semail')
    old_pass = request.POST['old_pass']
    new_pass = request.POST['new_pass']
    confirm_pass = request.POST['confirm_pass']
    
    if new_pass != confirm_pass:
        messages.success(request, 'New password and confirm password do not match!')
        return redirect(change_password)
    
    log_info = models.Login.objects.filter(user_name=email, password=old_pass).first()
    if not log_info:
        messages.success(request, 'Old password is incorrect!')
        return redirect(change_password)
    
    log_info.password = new_pass
    log_info.save()
    
    messages.success(request, 'Password updated successfully!')
    return redirect('admin_change_password')

def admin_profile(request):
    email = request.session.get('semail')
    user_details = models.Users.objects.filter(email=email).first()
    context = {
        'user_details': user_details
    }
    return render(request, 'admin/profile.html', context)

def admin_edit_profile(request):
    email = request.session.get('semail')
    user_details = models.Users.objects.filter(email=email).first()
    
    if request.method == 'POST':
        name = request.POST.get('name')
        new_email = request.POST.get('email')
        
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
        return redirect('admin_profile')
        
    context = {
        'user_details': user_details
    }
    return render(request, 'admin/edit_profile.html', context)
 
# Units CRUD
def units(request):
    uom = models.Units.objects.all()
    context = {
        'units': uom
    }
    return render(request, 'units/units.html', context)
def save_unit(request):
    unit_name = request.POST["unit_name"]
    
    sdata = models.Units(
        unit_name=unit_name 
    )
    sdata.save()
    log_activity(request, 'CREATE', 'units', sdata.id)
    messages.success(request, 'Unit created successfully!')
    return redirect(units)
def edit_unit(request, cid):
    sdata = models.Units.objects.get(id=cid)
    context = {
        "unit": sdata
    }
    return render(request, 'units/units_edit.html', context)
def update_unit(request):
    uid = request.POST['uid']
    name = request.POST['unit_name']
    
    sdata = models.Units.objects.get(id=uid)
    sdata.unit_name = name
    sdata.save()
    log_activity(request, 'UPDATE', 'units', uid)
    messages.success(request, 'Updated successfully!')
    return redirect(units)
def delete_unit(request, uid):
    sdata = models.Units.objects.get(id=uid)
    sdata.delete()
    log_activity(request, 'DELETE', 'units', uid)
    messages.success(request, 'Deleted successfully!!!!')
    return redirect(units)

# Categories CRUD
def categories(request):
    category_search = request.GET.get('category_search', '')
    cats_list = models.Categories.objects.all().order_by('-id')

    if category_search:
        cats_list = cats_list.filter(cat_name__icontains=category_search)

    # Paginate the categories (10 per page)
    paginator = Paginator(cats_list, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'categories': page_obj.object_list,
        'page_obj': page_obj,
        'total_count': paginator.count,
        'category_search': category_search,
    }

    if request.GET.get('ajax'):
        return render(request, 'categories/categories_table_partial.html', context)

    return render(request, 'categories/categories.html', context)
def add_category(request):
    return render(request, 'categories/add_category.html')
def save_category(request):
    cat_name = request.POST["cat_name"]
    
    sdata = models.Categories(
        cat_name=cat_name,
        status=1
    )
    sdata.save()
    log_activity(request, 'CREATE', 'categories', sdata.id)
    messages.success(request, 'Category created successfully!')
    return redirect(categories)
def edit_category(request, cid):
    sdata = models.Categories.objects.get(id=cid)
    context = {
        "category": sdata
    }
    return render(request, 'categories/edit_category.html', context)
def update_category(request):
    cid = request.POST['cid']
    name = request.POST['cat_name']
    status = request.POST['status']
    
    sdata = models.Categories.objects.get(id=cid)
    sdata.cat_name = name
    sdata.status = status
    sdata.save()
    log_activity(request, 'UPDATE', 'categories', cid)
    messages.success(request, 'Updated successfully!')
    return redirect(categories)
def delete_category(request, cid):
    sdata = models.Categories.objects.get(id=cid)
    sdata.delete()
    log_activity(request, 'DELETE', 'categories', cid)
    messages.success(request, 'Deleted successfully!!!!')
    return redirect(categories)

# Products CRUD
def products(request):
    from django.core.paginator import Paginator
    
    # Use raw SQL to join with categories
    prods = models.Products.objects.raw("""
        SELECT p.id, p.product_name, p.sku, p.price, 
               p.unit_id,u.unit_name, p.status, c.cat_name, p.cat_id
        FROM products p
        LEFT JOIN unit u on p.unit_id = u.unit_id
        LEFT JOIN categories c ON p.cat_id = c.id
    """)
    
    # Convert RawQuerySet to list for pagination
    prods_list = list(prods)
    
    # Paginate the products (15 per page)
    paginator = Paginator(prods_list, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    cats = models.Categories.objects.all()
    units_list = models.Units.objects.all()
    context = {
        'products': page_obj.object_list,
        'page_obj': page_obj,
        'categories': cats,
        'units': units_list,
        'total_pages': paginator.num_pages
    }
    return render(request, 'products/products.html', context)
def add_product(request):    
    cats = models.Categories.objects.all()
    units = models.Units.objects.all()
    context = {
        "categories": cats,
        "units": units
    }
    return render(request, 'products/add_products.html', context)
def save_product(request):
    product_name = request.POST["product_name"]
    sku = request.POST["sku"]
    cat_id = request.POST["cat_id"]
    price = request.POST["price"]
    unit = request.POST["unit"]
    
    # Check if SKU exists
    existing = models.Products.objects.filter(sku=sku).first()
    if existing:
        messages.success(request, 'Product SKU already exists!!!!!')
        return redirect('products')
    
    sdata = models.Products(
        product_name=product_name,
        sku=sku,
        cat_id=cat_id,
        price=price,
        unit_id=unit,
        status=1
    )
    sdata.save()
    log_activity(request, 'CREATE', 'products', sdata.id)
    messages.success(request, 'Product created successfully!')
    return redirect(products)
def edit_product(request, pid):
    sdata = models.Products.objects.get(id=pid)
    cats = models.Categories.objects.all()
    units = models.Units.objects.all()
    context = {
        "product": sdata,
        "categories": cats,
        "units": units
    }
    return render(request, 'products/products_edit.html', context)
def update_product(request):
    pid = request.POST['pid']
    product_name = request.POST['product_name']
    sku = request.POST['sku']
    cat_id = request.POST['cat_id']
    price = request.POST['price']
    unit = request.POST['unit']
    
    sdata = models.Products.objects.get(id=pid)
    sdata.product_name = product_name
    sdata.sku = sku
    sdata.cat_id = cat_id
    sdata.price = price
    sdata.unit_id = unit
    
    sdata.save()
    log_activity(request, 'UPDATE', 'products', pid)
    
    messages.success(request, 'Updated successfully!')
    return redirect(products)
def delete_product(request, pid):
    # Check if product exists in any PO, GRN, or Sales
    po_exists = models.PurchaseOrderItems.objects.filter(product_id=pid).exists()
    grn_exists = models.GRNItems.objects.filter(product_id=pid).exists()
    sales_exists = models.SaleItems.objects.filter(product_id=pid).exists()
    ledger_exists = models.StockLedger.objects.filter(product_id=pid).exists()
    adj_exists = models.StockAdjustment.objects.filter(product_id=pid).exists()
    
    if po_exists or grn_exists or sales_exists or ledger_exists or adj_exists:
        error_msg = "Cannot delete this product because it has entries in: "
        reasons = []
        if po_exists:
            reasons.append("Purchase Orders")
        if grn_exists:
            reasons.append("GRN (Stock IN)")
        if sales_exists:
            reasons.append("Sales (Stock OUT)")
        if ledger_exists:
            reasons.append("Stock Ledger")
        if adj_exists:
            reasons.append("Stock Adjustments")
        error_msg += ", ".join(reasons)
        messages.error(request, error_msg)
        return redirect(products)
    
    sdata = models.Products.objects.get(id=pid)
    sdata.delete()
    log_activity(request, 'DELETE', 'products', pid)
    messages.success(request, 'Deleted successfully!!!!')
    return redirect(products)
def disable_product(request, pid):
    sdata = models.Products.objects.get(id=pid)
    # Toggle status: 1 -> 0, 0 -> 1
    if sdata.status == 1:
        sdata.status = 0
        msg = 'Product disabled successfully!'
    else:
        sdata.status = 1
        msg = 'Product enabled successfully!'
        
    sdata.save()
    log_activity(request, 'DISABLE/ENABLE', 'products', pid)
    #messages.success(request, msg)
    return redirect(products)

# Suppliers CRUD
def suppliers(request):
    from django.core.paginator import Paginator
    
    email_search = request.GET.get('email_search', '')
    sups = models.Suppliers.objects.all().order_by('-id')
    
    if email_search:
        sups = sups.filter(email__istartswith=email_search)
    
    # Paginate the suppliers (10 per page)
    paginator = Paginator(sups, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'suppliers': page_obj.object_list,
        'page_obj': page_obj,
        'email_search': email_search
    }
    
    if request.GET.get('ajax'):
        return render(request, 'suppliers/suppliers_table_partial.html', context)
        
    return render(request, 'suppliers/suppliers.html', context)
def add_supplier(request):
    return render(request, 'suppliers/add_supplier.html')
def save_supplier(request):
    supplier_name = request.POST["supplier_name"]
    email = request.POST["email"]
    phone = request.POST["phone"]
    place = request.POST["place"]
    address = request.POST["address"]
    
    # Check if exists
    existing = models.Suppliers.objects.filter(email=email).first()
    if existing:
        messages.success(request, 'Supplier email already exists!!!!!')
        return redirect('suppliers')
    
    sdata = models.Suppliers(
        supplier_name=supplier_name,
        email=email,
        phone=phone,
        place=place,
        address=address
    )
    sdata.save()
    log_activity(request, 'CREATE', 'suppliers', sdata.id)
    messages.success(request, 'Supplier created successfully!')
    return redirect(suppliers)
def edit_supplier(request, sid):
    sdata = models.Suppliers.objects.get(id=sid)
    context = {
        "supplier": sdata
    }
    return render(request, 'suppliers/edit_supplier.html', context)
def update_supplier(request):
    sid = request.POST['sid']
    supplier_name = request.POST['supplier_name']
    email = request.POST['email']
    phone = request.POST['phone']
    place = request.POST['place']
    address = request.POST['address']
    
    sdata = models.Suppliers.objects.get(id=sid)
    sdata.supplier_name = supplier_name
    sdata.email = email
    sdata.phone = phone
    sdata.place = place
    sdata.address = address
    sdata.save()
    
    log_activity(request, 'UPDATE', 'suppliers', sid)
    
    messages.success(request, 'Updated successfully!')
    return redirect(suppliers)
def delete_supplier(request, sid):
    # Check if supplier has PurchaseOrders
    po_exists = models.PurchaseOrders.objects.filter(supplier_id=sid).exists()
    
    # Check if supplier has GRN entries (via PO)
    po_ids = models.PurchaseOrders.objects.filter(supplier_id=sid).values_list('id', flat=True)
    grn_exists = models.Grn.objects.filter(po_id__in=po_ids).exists()
    
    # Build error messages
    error_modules = []
    if po_exists:
        error_modules.append("Purchase Orders")
    if grn_exists:
        error_modules.append("Goods Receipt Notes (GRN)")
    
    if error_modules:
        error_message = f"Cannot delete supplier! It has entries in: {', '.join(error_modules)}"
        messages.error(request, error_message)
        return redirect('suppliers')
    
    # If no conflicts, proceed with deletion
    sdata = models.Suppliers.objects.get(id=sid)
    sdata.delete()
    log_activity(request, 'DELETE', 'suppliers', sid)
    messages.success(request, 'Supplier deleted successfully!')
    return redirect('suppliers')

# Purchase Orders CRUD
def purchase_orders(request):
    # Get all purchase orders with supplier names and totals
    cursor = connection.cursor()
    cursor.execute("""
        SELECT po.id, po.po_date, s.supplier_name, po.status_id, st.status,
               COALESCE(SUM(poi.total_price), 0) as po_total
        FROM purchase_orders po
        LEFT JOIN suppliers s ON po.supplier_id = s.id
        LEFT JOIN purchase_order_items poi ON po.id = poi.po_id
        LEFT JOIN status st ON po.status_id = st.id
        GROUP BY po.id, po.po_date, s.supplier_name,po.status_id, st.status
        ORDER BY po.id DESC
    """)
    pos = cursor.fetchall()
    # Convert to list for pagination
    # pos_list = list(pos)


    # Get all PO IDs
    po_ids = [po[0] for po in pos]

    # Get all GRN po_ids in one query
    grn_po_ids = set(
        models.Grn.objects.filter(po_id__in=po_ids)
        .values_list('po_id', flat=True)
    )

    
    po_data = []

    for po in pos:
        po_data.append({
            'id': po[0],
            'po_date': po[1],
            'supplier_name': po[2],
            'status_id': po[3],
            'status': po[4],
            'po_total': po[5],
            'grn_exists': po[0] in grn_po_ids
        })
         


        
    # Paginate the purchase orders (10 per page)
    paginator = Paginator(po_data, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Data needed for the "Add Purchase Order" modal
    sups = models.Suppliers.objects.all()
    prods = models.Products.objects.all()
    units = models.Units.objects.all()
    last_po = models.PurchaseOrders.objects.latest('id') if models.PurchaseOrders.objects.exists() else None
    next_id = (last_po.id + 1) if last_po else 1
    po_number = f"PO-{next_id:06d}"

    context = {
        'purchase_orders': page_obj.object_list,
        'page_obj': page_obj,
        'suppliers': sups,
        'products': prods,
        'units': units,
        'po_number': po_number,
    }
    return render(request, 'purchase_orders/purchase_orders.html', context)
def approve_po(request, poid, stat):
    try:
        po = models.PurchaseOrders.objects.get(id=poid) 
        po.status_id = stat
        po.save()  
        if stat == 2:
            log_activity(request, 'APPROVE', 'purchase_orders', poid)
            messages.success(request, 'Purchase Order Approved.')
        if stat == 3:
            log_activity(request, 'REJECTED', 'purchase_orders', poid)
            messages.success(request, 'Purchase Order Rejected')            
    except models.PurchaseOrders.DoesNotExist:
        messages.error(request, 'PO not found.') 
    return redirect(purchase_orders)
def add_purchase_order(request):
    sups = models.Suppliers.objects.all()
    prods = models.Products.objects.all()
    units = models.Units.objects.all()
    last_po = models.PurchaseOrders.objects.latest('id') if models.PurchaseOrders.objects.exists() else None
    next_id = (last_po.id + 1) if last_po else 1
    po_number = f"PO-{next_id:06d}"
    
    context = {
        'suppliers': sups,
        'products': prods,
        'units': units,
        'po_number': po_number
    }
    return render(request, 'purchase_orders/add_purchase_order.html', context)
def save_purchase_order(request):
    supplier_id = request.POST["supplier_id"]
    po_date = request.POST["po_date"]
    
    # Save Master PO
    po = models.PurchaseOrders(
        supplier_id=supplier_id,
        po_date=po_date,
        status_id=1,
        created_at=dt.now()
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
            u_name = units_sent[i] if i < len(units_sent) else ""
            
            models.PurchaseOrderItems.objects.create(
                po=po,
                product_id=product_ids[i],
                quantity=qty,
                unit_price=price,
                total_price=total,
                unit_id=u_name if u_name else None
            )
            
    log_activity(request, 'CREATE', 'purchase_orders', po.id)
    messages.success(request, 'Purchase Order created successfully!')
    return redirect(purchase_orders)
def edit_purchase_order(request, poid):
    po = get_object_or_404(models.PurchaseOrders, id=poid)

    postatus = get_object_or_404(models.DocStatus, id=po.status_id)

    # CHECK IF ANY GRN EXISTS
    has_grn = models.Grn.objects.filter(po_id=poid).exists()

    sups = models.Suppliers.objects.all()
    items = models.PurchaseOrderItems.objects.filter(po=poid)
    #products = models.Products.objects.all()

# Use raw SQL to join with products and units to get unit_name
    cursor = connection.cursor()
    cursor.execute("""
        SELECT p.id, p.product_name, p.unit_id, p.price, u.unit_name 
        FROM products p 
        LEFT JOIN unit u ON p.unit_id = u.unit_id
    """)
    items_raw = cursor.fetchall()
    
    # Map raw data to objects or list of dicts for template
    products = [] 
    for row in items_raw:
        item = {
            'id':row[0],
            'product_name': row[1],
            'unit_id': row[2],
            'price': row[3], 
            'unit_name': row[4]
        }
        products.append(item)

    units = models.Units.objects.all()

    context = {
        "po": po,
        "suppliers": sups,
        "items": items,
        "products": products,
        "units": units,
        "has_grn": has_grn,
        "status": postatus
    }
    return render(request, 'purchase_orders/purchase_orders_edit.html', context)
def update_purchase_order(request):
    if request.method == "POST":
        poid = request.POST.get('poid')
        po = get_object_or_404(models.PurchaseOrders, id=poid)

        if models.Grn.objects.filter(po_id=poid).exists():
            messages.error(request, "Update not allowed. GRN already exists for this PO.")
            return redirect('purchase_orders')

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
                quantity = int(quantities[i])
                price = float(unit_prices[i])
                total = quantity * price
                u_name = units_sent[i] if i < len(units_sent) else ""

                models.PurchaseOrderItems.objects.create(
                    po_id=poid,
                    product_id=product_ids[i],
                    quantity=quantity,
                    unit_price=price,
                    total_price=total,
                    unit_id=u_name if u_name else None
                )
                grand_total += total

        po.save() # Optional if no additional fields
        log_activity(request, 'UPDATE', 'purchase_orders', poid)
        messages.success(request, "Purchase Order Updated Successfully!")
        return redirect('purchase_orders')

    return redirect('purchase_orders')
def view_po_items(request, poid):
    #po = get_object_or_404(models.PurchaseOrders, id=poid)
     # Get purchase order data with status_name
    cursorpo = connection.cursor()
    cursorpo.execute("""
        SELECT pos.id,pos.po_date,pos.supplier_id, st.status
        FROM purchase_orders pos
        LEFT JOIN status st ON pos.status_id = st.id 
        WHERE pos.id = %s
    """, [poid])
    po_raw = cursorpo.fetchall()
    
    supplier = get_object_or_404(models.Suppliers, id=po_raw[0][2])

    po = [] 
    for porow in po_raw:
        po_ = {
            'id': porow[0],
            'po_date': porow[1],
            'supplier_id': porow[2],
            'status': porow[3] 
        }
        po.append(po_)    
    # Use raw SQL to join with products and units to get unit_name
    cursor = connection.cursor()
    cursor.execute("""
        SELECT poi.id, p.product_name, poi.quantity, poi.unit_price, poi.total_price, u.unit_name
        FROM purchase_order_items poi
        LEFT JOIN products p ON poi.product_id = p.id
        LEFT JOIN unit u ON poi.unit_id = u.unit_id
        WHERE poi.po_id = %s
    """, [poid])
    items_raw = cursor.fetchall()
    
    # Map raw data to objects or list of dicts for template
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
        'po': po,
        'supplier': supplier,
        'items': items,
        'grand_total': grand_total
    }
    return render(request, 'purchase_orders/view_po_items.html', context)
def delete_purchase_order(request, poid):
    sdata = models.PurchaseOrders.objects.get(id=poid)
    sdata.delete()
    log_activity(request, 'DELETE', 'purchase_orders', poid)
    messages.success(request, 'Deleted successfully!!!!')
    return redirect(purchase_orders)

# GRN CRUD
def grn_list(request):
    cursor = connection.cursor()
    cursor.execute("""
        SELECT g.id, g.grn_date, g.po_id, p.po_date, s.supplier_name, g1.grn_value as total, g.status_id, stat.status
        FROM grn g 
        LEFT JOIN purchase_orders p ON g.po_id = p.id
        LEFT JOIN (SELECT grn_id, SUM(grn_amount) as grn_value FROM grn_items GROUP BY grn_id) AS g1 ON g.id = g1.grn_id
        LEFT JOIN suppliers s ON p.supplier_id = s.id
        LEFT JOIN status stat ON g.status_id = stat.id
        ORDER BY g.id DESC
    """)
    grns = cursor.fetchall()
    paginator = Paginator(grns, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {'page_obj': page_obj}
    return render(request, 'grn/grn_list.html', context)
def view_grn_items(request, grnid):
    #po = get_object_or_404(models.PurchaseOrders, id=poid)
     # Get purchase order data with status_name
    cursorgrn = connection.cursor()
    cursorgrn.execute("""
        SELECT grn.id,grn.grn_date,grn.po_id,p.po_date,p.supplier_id,s.supplier_name, st.status
        FROM grn grn
        LEFT JOIN purchase_orders p on grn.po_id = p.id
                      LEFT JOIN Suppliers s on p.supplier_id = s.id
        LEFT JOIN status st ON grn.status_id = st.id 
        WHERE grn.id = %s
    """, [grnid])
    grn_raw = cursorgrn.fetchall()
    grn_status = grn_raw[0][6]
   # supplier = get_object_or_404(models.Suppliers, id=grn_raw[0][2])

    grns = [] 
    for grnrow in grn_raw:
        grn_ = {
            'id': grnrow[0],
            'grn_date': grnrow[1],
            'po_id': grnrow[2],
            'po_date': grnrow[3],
            'supplier_id': grnrow[4],
            'supplier_name': grnrow[5],
            'status': grnrow[6] 
        }
        grns.append(grn_)    
    # Use raw SQL to join with products and units to get unit_name
    cursor = connection.cursor()
    cursor.execute("""
        SELECT grn.product_id, p.product_name, grn.quantity, grn.rate, grn.grn_amount, u.unit_name
        FROM grn_items grn
        LEFT JOIN products p ON grn.product_id = p.id
        LEFT JOIN unit u ON grn.unit_id = u.unit_id
        WHERE grn.grn_id = %s
    """, [grnid])
    items_raw = cursor.fetchall()
    
    # Map raw data to objects or list of dicts for template
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
        'grns': grns,
        'items': items,
        'grand_total': grand_total,
        'grn_status':grn_status
    }
    return render(request, 'grn/view_grn_items.html', context)
def add_grn(request):
    pos = models.PurchaseOrders.objects.all()
    last_grn = models.Grn.objects.order_by('-id').first()
    next_grn_no = (last_grn.id + 1) if last_grn else 1
    grn_number = f"GRN-{next_grn_no:06d}"
    context = {'purchase_orders': pos, 'grn_no': grn_number}  
    return render(request, 'grn/add_grn.html', context)
def save_grn(request):     
    grn_date = request.POST["grn_date"]
    po_id = request.POST["po_id"]    
    # Save Master GRN
    grn = models.Grn( 
        grn_date=grn_date,
        po_id=po_id,
        status_id=1,
        created_at=dt.now()
    )
    grn.save()    
    # Save Items
    product_ids = request.POST.getlist('product_id[]')
    quantities = request.POST.getlist('quantity[]')
    poqs = request.POST.getlist('poq[]')
    bals = request.POST.getlist('bal[]')
    units_sent = request.POST.getlist('unit[]')
    prices = request.POST.getlist('rate[]')
    linetotal = request.POST.getlist('linetotal[]')

    for i in range(len(product_ids)):
        if product_ids[i] and i < len(quantities):
            try:
                qty = int(quantities[i])
                if qty <= 0: continue # Skip if no quantity entered
                
                poq = int(poqs[i]) if i < len(poqs) else 0
                balq = int(bals[i]) if i < len(bals) else 0
                price = float(prices[i]) if i < len(prices) else 0.0
                total = qty * price
                u_name = units_sent[i] if i < len(units_sent) else None
                
                models.GRNItems.objects.create(
                    grn=grn,
                    product_id=product_ids[i],
                    po_qty=poq,
                    bal_qty=balq,
                    quantity=qty,
                    rate=price,
                    grn_amount=total,
                    unit_id=u_name
                )
            except (ValueError, IndexError) as e:
                print(f"Skipping row {i} due to error: {e}")
                continue
            
    log_activity(request, 'CREATE', 'grn', grn.id)
    messages.success(request, 'GRN created successfully!')
    return redirect(grn_list)





    # if request.method == "POST":
    #     po_id = request.POST.get("po_id")
    #     product_ids = request.POST.getlist("product_id[]")
    #     qtys = request.POST.getlist("qty[]")
    #     for product_id, qty_value in zip(product_ids, qtys):
    #         if not qty_value.strip(): continue
    #         try:
    #             received_qty = int(qty_value)
    #         except ValueError: continue
    #         if received_qty <= 0: continue
    #         models.Grn.objects.create(po_id=po_id, product_id=product_id, qty=received_qty, status="Pending")
    #     return redirect("grn_list") 
def view_po_items_for_grn(request, poid):
    po = models.PurchaseOrders.objects.get(id=poid,status_id=2)
    supplier = models.Suppliers.objects.get(id=po.supplier_id)
    items = models.PurchaseOrderItems.objects.filter(po_id=poid)
    data = []
    for item in items:
        # received_data = models.Grn.objects.filter(po_id=poid, product_id=item.product_id).aggregate(total_received=Sum('qty'))
        received_data = models.GRNItems.objects.filter(
            grn_id__po_id=poid, 
            product_id=item.product_id
        ).exclude(grn__status_id=3).aggregate(total_received=Sum('quantity'))


        already_received = received_data['total_received'] or 0
        remaining_qty = item.quantity - already_received
       # units = models.Units.objects.filter(unit_id=item.product.unit_id)
        data.append({
            'product_id': item.product.id,
            'product_name': item.product.product_name,
            'ordered_qty': item.quantity,
            'already_received': already_received,
            'remaining_qty': remaining_qty,
            'unit': item.product.unit_id,
            'unit_name': item.unit.unit_name,
            'rate': float(item.unit_price),
            'total': float(0),
            'is_completed': remaining_qty <= 0
        })
    return JsonResponse({'supplier': supplier.supplier_name, 'products': data})
def edit_grn(request, gid):
    try:
        grn = models.Grn.objects.get(id=gid)
        if grn.status_id == 2: # 2 = Approved
            messages.error(request, 'Cannot edit Approved GRN.')
            return redirect('grn_list')
            
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
            "supplier": supplier
        }
        return render(request, 'grn/grn_edit.html', context)
    except models.Grn.DoesNotExist:
        messages.error(request, 'GRN not found.')
        return redirect('grn_list')

def update_grn(request):
    item_ids = request.POST.getlist('grn_id[]') # These are actually GRNItem IDs in the form
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
            item.quantity = qtys[i]
            # rate and grn_amount are derived or set during initial entry, 
            # but usually quantity change requires rate update too if we want accuracy.
            # For now, just fixing the AttributeErrors.
            item.grn_amount = float(item.rate or 0) * float(qtys[i] or 0)
            item.save()
            updated_count += 1
        except Exception as e:
            print(f"Error updating item {item_ids[i]}: {e}")
            continue
            
    log_activity(request, f"Batch Update {updated_count} GRN items", 'grn')
    messages.success(request, f'Updated {updated_count} GRN items.')
    return redirect('grn_list')
def delete_grn(request, gid):
    try:
        grn = models.Grn.objects.get(id=gid)
        if grn.status_id == 2:
            messages.error(request, 'Cannot delete Approved GRN.')
            return redirect('grn_list')
        if grn.status_id == 3:
            messages.error(request, 'Cannot delete Rejected GRN.')
            return redirect('grn_list')
        grn.delete()
        log_activity(request, 'DELETE', 'grn', gid)
        messages.success(request, 'Deleted successfully.')
    except models.Grn.DoesNotExist:
        messages.error(request, 'GRN not found.')
    return redirect('grn_list')

def approve_grn(request, gid, stat):
    try:
        grn = models.Grn.objects.get(id=gid)
        if grn.status_id != 1: # Only Pending can be acted upon
            messages.warning(request, 'GRN is not in pending status.')
            return redirect('grn_list')

        grn.status_id = stat
        grn.save()
        
        if int(stat) == 2: # Approved
            log_activity(request, 'APPROVE', 'grn', gid)
            # Update Stock
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
                    created_at=timezone.now()
                )
            messages.success(request, 'GRN Approved and Stock Updated successfully.')
        elif int(stat) == 3: # Rejected
            log_activity(request, 'REJECT', 'grn', gid)
            messages.success(request, 'GRN Rejected successfully.')
            
    except models.Grn.DoesNotExist:
        messages.error(request, 'GRN not found.')
    return redirect('grn_list')

# Sales CRUD
def sales_list(request):
    cursor = connection.cursor()
    cursor.execute("""
        SELECT s.id, s.sale_date, COALESCE(c.customer_name, 'Cash Customer'), stat.status,
               COALESCE(SUM(si.total), 0) as grand_total
        FROM sales s
        LEFT JOIN customers c ON s.customer_id = c.id
        LEFT JOIN sale_items si ON s.id = si.sale_id
                   LEFT JOIN status stat ON s.status_id = stat.id
        GROUP BY s.id, s.sale_date, c.customer_name, stat.status
        ORDER BY s.id DESC
    """)
    sales_list_all = cursor.fetchall()
    
    # Paginate the sales (10 per page)
    paginator = Paginator(sales_list_all, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'sales': page_obj.object_list,
        'page_obj': page_obj,
        'customers': models.Customers.objects.all(), 
        'products': models.Products.objects.all()
    }
    return render(request, 'sales/sales_list.html', context)
def view_sale_items(request, sid):
    # Get sale data
    sale = get_object_or_404(models.Sales, id=sid)
    customer = None
    if sale.customer_id and int(sale.customer_id) != 0:
        customer = models.Customers.objects.filter(id=sale.customer_id).first()
    else:
        customer = {'customer_name': 'Cash Customer', 'phone': '-', 'email': '-', 'address': '-'}

    # Get sale items with product names and unit names
    cursor = connection.cursor()
    cursor.execute("""
        SELECT si.id, p.product_name, si.qty, si.price, si.total, u.unit_name
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
            'product_name': row[1],
            'qty': row[2],
            'price': row[3],
            'subtotal': row[4],
            'unit': row[5]
        }
        items.append(item)
        if row[4]:
            grand_total += float(row[4])

    context = {
        'sale': sale,
        'customer': customer,
        'items': items,
        'grand_total': grand_total
    }
    return render(request, 'sales/view_sale_items.html', context)
def add_sale(request):
    last_sale = models.Sales.objects.latest('id') if models.Sales.objects.exists() else None
    next_id = (last_sale.id + 1) if last_sale else 1
    sale_number = f"SALE-{next_id:06d}"
    
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
        'products': products, #models.Products.objects.all(),
        'units': models.Units.objects.all(),
        'sale_number': sale_number
    }
    return render(request, 'sales/add_sale.html', context)
def save_sale(request):
    sdata = models.Sales.objects.create(
        customer_id=request.POST["customer_id"], sale_date=request.POST["sale_date"],
        status_id=2, created_at=dt.now()
    )
    product_ids = request.POST.getlist("product_id[]")
    unit_ids = request.POST.getlist("unit[]")
    qtys = request.POST.getlist("qty[]")
    for i in range(len(product_ids)):
        if i >= len(qtys) or not product_ids[i] or not qtys[i]: continue
        try:
            prod = models.Products.objects.get(id=product_ids[i])
            price = prod.price or 0
            uom = prod.unit_id
        except: price = 0
        total = float(price) * float(qtys[i])
        models.SaleItems.objects.create(sale_id=sdata.id, product_id=product_ids[i], unit_id=uom, qty=qtys[i], price=price, total=total)
        models.StockLedger.objects.create(product_id=product_ids[i], voucher_type='SALE', voucher_id=sdata.id,unit_id=uom,
                qty=qtys[i], in_out='OUT', created_at=dt.now()
            )
            
        # Update Product Stock (Decrease for Sale)
        prod.stock_qty = (prod.stock_qty or 0) - int(qtys[i])
        prod.save()
    log_activity(request, 'CREATE', 'sales', sdata.id)
   # messages.success(request, 'Sale created as Pending. Please Approve to deduct stock.')
   
    return redirect(sales_list)
def approve_sale(request, sid):
    try:
        sale = models.Sales.objects.get(id=sid)
        if sale.status_id == 2: # 2 = Approved
            messages.warning(request, 'Sale already approved.')
            return redirect(sales_list)
        items = models.SaleItems.objects.filter(sale_id=sale.id)
        for item in items:
            prod = models.Products.objects.get(id=item.product_id)
            if (prod.stock_qty or 0) < item.qty:
                messages.error(request, f'Insufficient stock for {prod.product_name}.')
                return redirect(sales_list)
        for item in items:
            models.StockLedger.objects.create(
                product_id=item.product_id, voucher_type='SALE', voucher_id=sale.id,
                qty=item.qty, in_out='OUT', created_at=dt.now()
            )
            prod = models.Products.objects.get(id=item.product_id)
            prod.stock_qty = (prod.stock_qty or 0) - int(item.qty)
            prod.save()
        sale.status_id = 2 # 2 = Approved
        sale.save()
        log_activity(request, 'APPROVE', 'sales', sid)
        messages.success(request, 'Sale Approved and Stock Deducted.')
    except models.Sales.DoesNotExist: messages.error(request, 'Sale not found.')
    return redirect(sales_list)
def delete_sale(request, sid):
    try:
        sale = models.Sales.objects.get(id=sid)
        if sale.status_id == 2:
            messages.error(request, 'Cannot delete Approved Sale.')
            return redirect(sales_list)
        models.SaleItems.objects.filter(sale_id=sale.id).delete()
        sale.delete()
        log_activity(request, 'DELETE', 'sales', sid)
        messages.success(request, 'Sale deleted successfully.')
    except models.Sales.DoesNotExist: messages.error(request, 'Sale not found.')
    return redirect(sales_list)
def edit_sale(request, sid):
    try:
        sale = models.Sales.objects.get(id=sid)
        if sale.status_id == 2: return redirect(sales_list)
        context = {
            'sale': sale, 'sale_items': models.SaleItems.objects.filter(sale_id=sale.id),
            'products': models.Products.objects.all(), 'customers': models.Customers.objects.all(),
            'units': models.Units.objects.all()
        }
        return render(request, 'sales/sales_edit.html', context)
    except models.Sales.DoesNotExist: return redirect(sales_list)
def update_sale(request):
    try:
        sale = models.Sales.objects.get(id=request.POST['sale_id'])
        if sale.status_id == 2: return redirect(sales_list)
        sale.customer_id = request.POST['customer_id']
        sale.sale_date = request.POST['sale_date']
        sale.save()
        item_ids, product_ids, qtys = request.POST.getlist('item_id[]'), request.POST.getlist('product_id[]'), request.POST.getlist('qty[]')
        for i in range(len(item_ids)):
            try:
                item = models.SaleItems.objects.get(id=item_ids[i])
                if item.sale_id != sale.id: continue
                item.product_id = product_ids[i]
                item.qty = qtys[i]
                prod = models.Products.objects.get(id=item.product_id)
                item.price = prod.price or 0
                item.total = float(item.price) * float(item.qty)
                item.save()
            except: continue
        log_activity(request, 'UPDATE', 'sales', sale.id)
        messages.success(request, 'Sale updated.')
    except: pass
    return redirect(sales_list)
def delete_sale_item(request, item_id):
    try:
        item = models.SaleItems.objects.get(id=item_id)
        sale = models.Sales.objects.get(id=item.sale_id)
        if sale.status_id == 2: return redirect(edit_sale, sid=sale.id)
        item.delete()
        messages.success(request, 'Item removed.')
        return redirect(edit_sale, sid=sale.id)
    except: return redirect(sales_list)

# Reports
def stock_view(request):
    cursor = connection.cursor()
    cursor.execute("""
        SELECT p.id, p.product_name, p.sku, p.unit_id,uom.unit_name,
               COALESCE(SUM(CASE WHEN sl.in_out = 'IN' THEN sl.qty ELSE 0 END), 0) as total_in,
               COALESCE(SUM(CASE WHEN sl.in_out = 'OUT' THEN sl.qty ELSE 0 END), 0) as total_out,
               (COALESCE(SUM(CASE WHEN sl.in_out = 'IN' THEN sl.qty ELSE 0 END), 0) - 
                COALESCE(SUM(CASE WHEN sl.in_out = 'OUT' THEN sl.qty ELSE 0 END), 0)) as current_stock
        FROM products p
        LEFT JOIN stock_ledger sl ON p.id = sl.product_id
        LEFT JOIN unit uom on p.unit_id = uom.unit_id
        GROUP BY p.id, p.product_name, p.sku, p.unit_id,uom.unit_name
        ORDER BY p.product_name
    """)
    report_data = cursor.fetchall()
    
    # Paginate the data (8 per page)
    paginator = Paginator(report_data, 8)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'stock_data': page_obj.object_list,
        'page_obj': page_obj
    }
    return render(request, 'reports/stock_view.html', context)
def purchase_report(request):
    cursor = connection.cursor()
    cursor.execute("""
        SELECT po.id, po.po_date, s.supplier_name, po.status_id,stat.status,COUNT(gg.id) as grncount,g.total_qty 
        FROM purchase_orders po
        LEFT JOIN suppliers s ON po.supplier_id = s.id
        LEFT JOIN grn gg on po.id = gg.po_id
        LEFT JOIN (SELECT  grn_id,sum(quantity) as total_qty from grn_items group by  grn_id) g ON gg.id = g. grn_id
        LEFT JOIN status stat on po.status_id = stat.id
        GROUP BY po.id, po.po_date, s.supplier_name, po.status_id
        ORDER BY po.id DESC
    """)
    report_data = cursor.fetchall()
    
    # Paginate the data (8 per page)
    paginator = Paginator(report_data, 8)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'purchase_data': page_obj.object_list,
        'page_obj': page_obj
    }
    return render(request, 'reports/purchase_report.html', context)
def sales_report(request):
    cursor = connection.cursor()
    cursor.execute("""
        SELECT s.id, s.sale_date, c.customer_name, ss.SalesTotal
        FROM sales s
        INNER JOIN (SELECT sale_id,SUM(total) as SalesTotal FROM sale_items group by sale_id) ss ON S.id = ss.sale_id
        LEFT JOIN customers c ON s.customer_id = c.id 
        ORDER BY s.sale_date DESC
    """)
    report_data = cursor.fetchall()
    
    # Paginate the data (8 per page)
    paginator = Paginator(report_data, 8)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'sales_data': page_obj.object_list,
        'page_obj': page_obj
    }
    return render(request, 'reports/sales_report.html', context)
def stock_report(request):
    cursor = connection.cursor()
    cursor.execute("""
        SELECT sl.id, sl.voucher_type, sl.voucher_id, p.product_name,uom.unit_name, sl.qty, sl.in_out, sl.created_at
        FROM stock_ledger sl
        LEFT JOIN products p ON sl.product_id = p.id
                   LEFT JOIN unit uom on sl.unit_id = uom.unit_id
        ORDER BY sl.created_at DESC
    """)
    report_data = cursor.fetchall()
    
    # Paginate the data (8 per page)
    paginator = Paginator(report_data, 8)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'ledger_data': page_obj.object_list,
        'page_obj': page_obj
    }
    return render(request, 'reports/stock_report.html', context)
# Audit
def audit_logs(request):
    logs_list = models.AuditLogs.objects.all().order_by('-created_at')
    
    # Paginate the logs (20 per page)
    paginator = Paginator(logs_list, 8)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'logs': page_obj.object_list,
        'page_obj': page_obj
    }
    return render(request, 'audit/audit_logs.html', context)

# CSV Exports
def purchase_report_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="purchase_report.csv"'
    writer = csv.writer(response)
    writer.writerow(['PO ID', 'Date', 'Supplier', 'Status', 'GRN Count', 'Total Qty'])
    cursor = connection.cursor()
    cursor.execute("""
        SELECT CONCAT('PO-',  RIGHT(CONCAT('0000000', po.id), 6)) as v,po.po_date, s.supplier_name, stat.status,COUNT(gg.id) as grncount,IFNULL(g.total_qty,0) AS total_qty
        FROM purchase_orders po
        LEFT JOIN suppliers s ON po.supplier_id = s.id
        LEFT JOIN grn gg on po.id = gg.po_id
        LEFT JOIN (SELECT  grn_id,sum(quantity) as total_qty from grn_items group by  grn_id) g ON gg.id = g. grn_id
        LEFT JOIN status stat on po.status_id = stat.id
        GROUP BY po.id, po.po_date, s.supplier_name, po.status_id
        ORDER BY po.id
    """)
    for row in cursor.fetchall(): writer.writerow(row)
    return response
def sales_report_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sales_report.csv"'
    writer = csv.writer(response)
    writer.writerow(['Sale ID', 'Date', 'Customer', 'Sales Value'])
    cursor = connection.cursor()
    cursor.execute("""                   
        SELECT CONCAT('SALE-',  RIGHT(CONCAT('0000000', s.id), 6)) as v, s.sale_date, c.customer_name, ss.SalesTotal
        FROM sales s
        INNER JOIN (SELECT sale_id,SUM(total) as SalesTotal FROM sale_items group by sale_id) ss ON S.id = ss.sale_id
        LEFT JOIN customers c ON s.customer_id = c.id 
        ORDER BY s.sale_date ASC 
    """)
    for row in cursor.fetchall(): writer.writerow(row)
    return response
def stock_report_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="stock_ledger.csv"'
    writer = csv.writer(response)
    writer.writerow(['Voucher', 'Product', 'Unit', 'Quantity', 'In/Out', 'Date'])
    cursor = connection.cursor()
    cursor.execute("""                   
        SELECT CONCAT(sl.voucher_type, '-',  RIGHT(CONCAT('0000000', sl.voucher_id), 6)) as v, p.product_name,uom.unit_name, sl.qty, sl.in_out, sl.created_at
        FROM stock_ledger sl
        LEFT JOIN products p ON sl.product_id = p.id
                   LEFT JOIN unit uom on sl.unit_id = uom.unit_id
        ORDER BY sl.created_at ASC LIMIT 1000 
    """)
    for row in cursor.fetchall(): writer.writerow(row)
    return response
def stock_summary_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="stock_summary.csv"'
    writer = csv.writer(response)
    writer.writerow(['SKU', 'Product Name', 'Unit', 'IN', 'OUT', 'Current Stock', 'Status'])
    cursor = connection.cursor()
    cursor.execute("""         
        SELECT p.id, p.product_name, p.sku,uom.unit_name,
               COALESCE(SUM(CASE WHEN sl.in_out = 'IN' THEN sl.qty ELSE 0 END), 0) as total_in,
               COALESCE(SUM(CASE WHEN sl.in_out = 'OUT' THEN sl.qty ELSE 0 END), 0) as total_out,
               (COALESCE(SUM(CASE WHEN sl.in_out = 'IN' THEN sl.qty ELSE 0 END), 0) - 
                COALESCE(SUM(CASE WHEN sl.in_out = 'OUT' THEN sl.qty ELSE 0 END), 0)) as current_stock
        FROM products p
        LEFT JOIN stock_ledger sl ON p.id = sl.product_id
        LEFT JOIN unit uom on p.unit_id = uom.unit_id
        GROUP BY p.id, p.product_name, p.sku, p.unit_id
        ORDER BY p.product_name
    """)
    for row in cursor.fetchall(): writer.writerow(row)
    return response


# Customers
def customers(request):
    email_search = request.GET.get('email_search', '')
    customers_list = models.Customers.objects.all().order_by('-id')
    
    if email_search:
        customers_list = customers_list.filter(email__istartswith=email_search)
    
    # Paginate the customers (10 per page)
    paginator = Paginator(customers_list, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'customers': page_obj.object_list,
        'page_obj': page_obj,
        'email_search': email_search
    }
    
    if request.GET.get('ajax'):
        return render(request, 'customers/customers_table_partial.html', context)
        
    return render(request, 'customers/customers.html', context)
def add_customer(request):
    return render(request, 'customers/add_customer.html')
def save_customer(request):
    if request.method == "POST":
        if models.Customers.objects.filter(phone=request.POST['phone']).exists():
            messages.error(request, 'Customer with this phone already exists!')
            return redirect(customers)
        cust = models.Customers.objects.create(
            customer_name=request.POST['customer_name'], phone=request.POST['phone'],
            email=request.POST.get('email', ''), place=request.POST.get('place', ''),
            address=request.POST.get('address', ''), created_at=dt.now()
        )
        log_activity(request, 'CREATE', 'customers', cust.id)
        messages.success(request, 'Customer added successfully!')
    return redirect(customers)
def edit_customer(request, cid):
    return render(request, 'customers/edit_customer.html', {'customer': models.Customers.objects.get(id=cid)})
def update_customer(request):
    if request.method == "POST":
        cust = models.Customers.objects.get(id=request.POST['cid'])
        cust.customer_name, cust.phone = request.POST['customer_name'], request.POST['phone']
        cust.email, cust.place, cust.address = request.POST.get('email', ''), request.POST.get('place', ''), request.POST.get('address', '')
        cust.save()
        log_activity(request, 'UPDATE', 'customers', cust.id)
        messages.success(request, 'Customer updated successfully!')
    return redirect(customers)
def delete_customer(request, cid):
    models.Customers.objects.get(id=cid).delete()
    log_activity(request, 'DELETE', 'customers', cid)
    messages.success(request, 'Customer deleted successfully!')
    return redirect(customers)
def view_customer_history(request, cid):
    cursor = connection.cursor()
    cursor.execute("""
        SELECT s.id, s.sale_date, p.product_name, sl.qty
        FROM sales s
        LEFT JOIN stock_ledger sl ON s.id = sl.voucher_id AND sl.voucher_type = 'SALE'
        LEFT JOIN products p ON sl.product_id = p.id
        WHERE s.customer_id = %s ORDER BY s.sale_date DESC
    """, [cid])
    return render(request, 'customers/customer_history.html', {'customer': models.Customers.objects.get(id=cid), 'history': cursor.fetchall()})

# Alerts
def view_all_alerts(request):
    cursor = connection.cursor()
    cursor.execute("""
        SELECT p.id, p.product_name, p.sku, p.reorder_level,
               p.stock_qty as current_stock
        FROM products p
        WHERE p.stock_qty <= IFNULL(p.reorder_level, 0)
    """)
    alerts_data = cursor.fetchall()
    
    # Paginate the data (8 per page)
    paginator = Paginator(alerts_data, 8)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'alerts': page_obj.object_list,
        'page_obj': page_obj
    }
    return render(request, 'alerts/alerts.html', context)
def configure_alerts(request):
    products_list = models.Products.objects.all().order_by('product_name')
    
    # Paginate the products (8 per page)
    paginator = Paginator(products_list, 8)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'products': page_obj.object_list,
        'page_obj': page_obj
    }
    return render(request, 'alerts/configure_alerts.html', context)
def update_alert_threshold(request):
    if request.method == "POST":
        prod = models.Products.objects.get(id=request.POST['pid'])
        prod.reorder_level = request.POST['reorder_level']
        prod.save()
        log_activity(request, 'UPDATE_THRESHOLD', 'products', prod.id)
        messages.success(request, 'Threshold updated successfully!')
    return redirect(configure_alerts)

import csv # Moved import to top-level or ensure it's there
