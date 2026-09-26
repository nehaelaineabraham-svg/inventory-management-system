from django.urls import path
from . import views

urlpatterns = [
    # Staff Dashboard
    path('dashboard/', views.staff_dashboard, name='staff_dashboard'),
    
    # View Products (Read-only)
    path('products/', views.view_products, name='staff_products'),
    
    # Enter GRN (Stock IN)
    path('grn_list/', views.staff_grn_list, name='staff_grn_list'),
    path('enter_grn/', views.enter_grn, name='staff_enter_grn'),
    path('save_grn/', views.save_grn, name='staff_save_grn'),
    path('edit_grn/<int:gid>/', views.edit_grn, name='staff_edit_grn'),
    path('view_grn_items/<int:gid>/', views.staff_view_grn_items, name='staff_view_grn_items'),
    path('update_grn/', views.update_grn, name='staff_update_grn'),
    path('delete_grn/<int:gid>/', views.delete_grn, name='staff_delete_grn'),
    path('view_po_items_for_grn/<int:poid>/', views.staff_view_po_items_for_grn, name='staff_view_po_items_for_grn'),
    
    # Create Sales (Stock OUT)
    path('sales_list/', views.staff_sales_list, name='staff_sales_list'),
    path('view_sale_items/<int:sid>/', views.staff_view_sale_items, name='staff_view_sale_items'),
    path('create_sales/', views.create_sales, name='staff_create_sales'),
    path('save_sale/', views.save_sale, name='staff_save_sale'),
    path('approve_sale/<int:sid>/', views.approve_sale, name='staff_approve_sale'),
    path('edit_sale/<int:sid>/', views.edit_sale, name='staff_edit_sale'),
    path('update_sale/', views.update_sale, name='staff_update_sale'),
    path('delete_sale/<int:sid>/', views.delete_sale, name='staff_delete_sale'),
    path('delete_sale_item/<int:item_id>/', views.delete_sale_item, name='staff_delete_sale_item'),
    
    # View Own Transactions
    path('transactions/', views.view_transactions, name='staff_transactions'),
    path('transactions/csv/', views.export_transactions_csv, name='staff_transactions_csv'),
    
    # Logout
    path('logout/', views.staff_logout, name='staff_logout'),
    
    # Categories
    path('categories/', views.view_categories, name='staff_categories'),
    
    # Damage Report
    path('damage_report/', views.report_damaged_items, name='staff_damage_report'),
    
    # Invoice
    path('invoice/<int:sale_id>', views.generate_sales_invoice, name='staff_sales_invoice'),
    
    # Stock Adjustment
    path('stock_adjustment/', views.update_stock_quantity, name='staff_stock_adjustment'),
    
    # Alerts
    path('stock_alerts/', views.receive_stock_alerts, name='staff_stock_alerts'),
    path('send_reminder/', views.send_stock_reminder, name='staff_send_reminder'),
    path('expiry_alerts/', views.receive_expiry_alerts, name='staff_expiry_alerts'),
    
    # Reports
    path('stock_report/', views.view_basic_stock_reports, name='staff_stock_report'),
    path('stock_report/csv/', views.export_stock_report_csv, name='staff_stock_report_csv'),
    
    # AJAX
    path('get_stock/', views.get_product_stock_ajax, name='get_product_stock_ajax'),
]
