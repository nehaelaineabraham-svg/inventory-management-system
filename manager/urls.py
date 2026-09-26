from django.urls import path
from . import views

urlpatterns = [
    # Manager Dashboard
    path('dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('profile/', views.manager_profile, name='manager_profile'),
    path('edit_profile/', views.manager_edit_profile, name='manager_edit_profile'),
    
    # View Products (Read-only)
    path('products/', views.view_products, name='manager_products'),
    
    # View Stock
    path('stock/', views.view_stock, name='manager_stock'),
    
    # View Reports
    path('purchase_report/', views.view_purchase_report, name='manager_purchase_report'),
    path('sales_report/', views.view_sales_report, name='manager_sales_report'),
    
    # Approve Purchase Orders
    path('approve_po/', views.approve_purchase_orders, name='manager_approve_po'),
    path('update_po_status/<int:poid>', views.update_po_status, name='manager_update_po_status'),
    
    # Logout
    path('logout/', views.manager_logout, name='manager_logout'),
    
    # Categories
    path('categories/', views.view_categories, name='manager_categories'),
    
    # Purchase Orders
    path('approve_po/', views.approve_purchase_orders, name='manager_approve_po'),
    path('view_po_items/<int:poid>/', views.manager_view_po_items, name='manager_view_po_items'),
    path('approve_po_action/<int:poid>/<int:stat>/', views.manager_approve_po_action, name='manager_approve_po_action'),
    path('delete_po/<int:poid>/', views.manager_delete_purchase_order, name='manager_delete_po'),
    
    path('create_po/', views.create_purchase_order, name='manager_create_po'),
    path('save_po/', views.save_purchase_order, name='manager_save_po'),
    path('edit_po/<int:poid>', views.edit_purchase_order, name='manager_edit_po'),
    path('update_po/', views.update_purchase_order, name='manager_update_po'),
    path('track_po/<int:poid>', views.track_purchase_order_status, name='manager_track_po'),
    
    # Analytics & reports
    path('supplier_performance/', views.review_supplier_performance, name='manager_supplier_performance'),
    path('customer_trends/', views.view_customer_sales_trends, name='manager_customer_trends'),
    path('purchase_analytics/', views.view_purchase_analytics, name='manager_purchase_analytics'),
    
    # Export Reports
    path('purchase_report/csv/', views.purchase_report_csv, name='manager_purchase_report_csv'),
    path('sales_report/csv/', views.sales_report_csv, name='manager_sales_report_csv'),
    path('supplier_performance/csv/', views.supplier_performance_csv, name='manager_supplier_performance_csv'),
    path('purchase_analytics/csv/', views.purchase_analytics_csv, name='manager_purchase_analytics_csv'),
    path('alerts/csv/', views.alerts_csv, name='manager_alerts_export_csv'),
    
    # Alerts & Logs
    path('alerts/', views.view_alerts, name='manager_alerts'),
    path('activity_logs/', views.view_related_activity_logs, name='manager_activity_logs'),
    
    # Trends (Redirect)
    path('stock_trends/', views.view_stock_trends, name='manager_stock_trends'),

    # Change Password
    path('change_password/', views.manager_change_password, name='manager_change_password'),
    path('update_password/', views.manager_update_password, name='manager_update_password'),

    # Approve GRN
    path('approve_grn/', views.manager_approve_grn, name='manager_approve_grn'),
    path('approve_grn_action/<int:gid>/<int:stat>/', views.manager_approve_grn_action, name='manager_approve_grn_action'),
    path('view_grn_items/<int:gid>/', views.manager_view_grn_items, name='manager_view_grn_items'),

    # Approve Stock Adjustments
    path('approve_adjustments/', views.manager_approve_adjustments, name='manager_approve_adjustments'),
    path('approve_adjustment_action/<int:aid>/<int:stat>/', views.manager_approve_adjustment_action, name='manager_approve_adjustment_action'),
    path('view_adjustment/<int:aid>/', views.manager_view_adjustment_details, name='manager_view_adjustment'),
    
    # Stock Reminders
    path('stock_reminders/', views.view_stock_reminders, name='manager_stock_reminders'),
    path('mark_reminder_seen/<int:rid>/', views.mark_reminder_seen, name='manager_mark_reminder_seen'),
    path('stock_reminder_detail/<int:rid>/', views.reminder_detail, name='manager_stock_reminder_detail'),
]
