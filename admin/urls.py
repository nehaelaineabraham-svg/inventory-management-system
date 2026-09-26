from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
   path('admin/', views.admin_dashboard, name='admin_dashboard'),
   
   # Users CRUD
   path('users/', views.users, name='users'),
   path('save_user/', views.save_user, name='save_user'),
   path('edit_user/<int:uid>', views.edit_user, name='edit_user'),
   path('update_user/', views.update_user, name='update_user'),
   path('delete_user/<int:uid>', views.delete_user, name='delete_user'),
   path('activate_user/<int:uid>', views.activate_user, name='activate_user'),
   path('deactivate_user/<int:uid>', views.deactivate_user, name='deactivate_user'),
   path('user_activity_logs/', views.user_activity_logs, name='user_activity_logs'),
   
   # Customers CRUD
   path('customers/', views.customers, name='customers'),
   path('add_customer/', views.add_customer, name='add_customer'),
   path('save_customer/', views.save_customer, name='save_customer'),
   path('edit_customer/<int:cid>', views.edit_customer, name='edit_customer'),
   path('update_customer/', views.update_customer, name='update_customer'),
   path('delete_customer/<int:cid>', views.delete_customer, name='delete_customer'),
   path('view_customer_history/<int:cid>', views.view_customer_history, name='view_customer_history'),
   
   # Change Password
   path('change_password/', views.change_password, name='admin_change_password'),
   path('update_pass_admin/', views.update_pass_admin, name='update_pass_admin'),
   
   # Profile
   path('profile/', views.admin_profile, name='admin_profile'),
   path('edit_profile/', views.admin_edit_profile, name='admin_edit_profile'),
   
   # Categories CRUD
   path('categories/', views.categories, name='categories'),
   path('add_category/', views.add_category, name='add_category'),
   path('save_category/', views.save_category, name='save_category'),
   path('edit_category/<int:cid>', views.edit_category, name='edit_category'),
   path('update_category/', views.update_category, name='update_category'),
   path('delete_category/<int:cid>', views.delete_category, name='delete_category'),
   
   # Products CRUD
   path('products/', views.products, name='products'),
   path('add_product/', views.add_product, name='add_product'),
   path('save_product/', views.save_product, name='save_product'),
   path('edit_product/<int:pid>', views.edit_product, name='edit_product'),
   path('update_product/', views.update_product, name='update_product'),
   path('delete_product/<int:pid>', views.delete_product, name='delete_product'),
   path('disable_product/<int:pid>', views.disable_product, name='disable_product'),
   
   # Suppliers CRUD
   path('suppliers/', views.suppliers, name='suppliers'),
   path('add_supplier/', views.add_supplier, name='add_supplier'),
   path('save_supplier/', views.save_supplier, name='save_supplier'),
   path('edit_supplier/<int:sid>', views.edit_supplier, name='edit_supplier'),
   path('update_supplier/', views.update_supplier, name='update_supplier'),
   path('delete_supplier/<int:sid>', views.delete_supplier, name='delete_supplier'),
   
   # Purchase Orders CRUD
   path('purchase_orders/', views.purchase_orders, name='purchase_orders'),
   path('add_purchase_order/', views.add_purchase_order, name='add_purchase_order'),
   path('view_po_items/<int:poid>', views.view_po_items, name='view_po_items'),
   path('save_purchase_order/', views.save_purchase_order, name='save_purchase_order'),
   path('approve_po/<int:poid>/<int:stat>', views.approve_po, name='approve_po'),
   path('edit_purchase_order/<int:poid>', views.edit_purchase_order, name='edit_purchase_order'),
   path('update_purchase_order/', views.update_purchase_order, name='update_purchase_order'),
   path('delete_purchase_order/<int:poid>', views.delete_purchase_order, name='delete_purchase_order'),
   
   # GRN (Goods Receipt Note)
   path('grn/', views.grn_list, name='grn_list'),
   path('view_grn_items/<int:grnid>', views.view_grn_items, name='view_grn_items'),
   path('add_grn/', views.add_grn, name='add_grn'),
   path('save_grn/', views.save_grn, name='save_grn'),
   path('approve_grn/<int:gid>/<int:stat>', views.approve_grn, name='approve_grn'),
   path('edit_grn/<int:gid>', views.edit_grn, name='edit_grn'),
   path('update_grn/', views.update_grn, name='update_grn'),   
   path('view_po_items_for_grn/<int:poid>/', views.view_po_items_for_grn, name='view_po_items_for_grn'),
   path('delete_grn/<int:gid>', views.delete_grn, name='delete_grn'),
   
   # Sales (Stock OUT)
   path('sales/', views.sales_list, name='sales_list'),
   path('view_sale_items/<int:sid>', views.view_sale_items, name='view_sale_items'),
   path('save_sale/', views.save_sale, name='save_sale'),
   path('add_sale/', views.add_sale, name='add_sale'),
   path('approve_sale/<int:sid>', views.approve_sale, name='approve_sale'),
   path('edit_sale/<int:sid>', views.edit_sale, name='edit_sale'),
   path('update_sale/', views.update_sale, name='update_sale'),
   path('delete_sale/<int:sid>', views.delete_sale, name='delete_sale'),
   path('delete_sale_item/<int:item_id>', views.delete_sale_item, name='delete_sale_item'),
   
   # Stock & Reports
   path('stock_view/', views.stock_view, name='stock_view'),
   path('purchase_report/', views.purchase_report, name='purchase_report'),
   path('sales_report/', views.sales_report, name='sales_report'),
   path('stock_report/', views.stock_report, name='stock_report'),
   
   # Export Reports
   path('purchase_report/csv/', views.purchase_report_csv, name='purchase_report_csv'),
   path('sales_report/csv/', views.sales_report_csv, name='sales_report_csv'),
   path('stock_report/csv/', views.stock_report_csv, name='stock_report_csv'),
   path('stock_view/csv/', views.stock_summary_csv, name='stock_summary_csv'),
   
   # Audit & Security
   path('audit_logs/', views.audit_logs, name='audit_logs'),
   
   # Alerts
   path('alerts/', views.view_all_alerts, name='view_all_alerts'),
   path('configure_alerts/', views.configure_alerts, name='configure_alerts'),
   path('update_alert_threshold/', views.update_alert_threshold, name='update_alert_threshold'),
   
#    path('logout/', views.logout_view, name='logout'),
]
