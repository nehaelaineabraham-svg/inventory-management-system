# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class AuditLogs(models.Model):
    id = models.BigAutoField(primary_key=True)
    user_id = models.BigIntegerField(blank=True, null=True)
    action = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()
    table_name = models.CharField(max_length=50, blank=True, null=True)
    record_id = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'audit_logs'


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.IntegerField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.IntegerField()
    is_active = models.IntegerField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'auth_user'


class AuthUserGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user', 'group'),)


class AuthUserUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user', 'permission'),)


class DocStatus(models.Model):
    id = models.BigAutoField(primary_key=True)
    status = models.CharField(max_length=100, blank=True, null=True) 

    class Meta:
        managed = False
        db_table = 'status'

class Categories(models.Model):
    id = models.BigAutoField(primary_key=True)
    cat_name = models.CharField(max_length=100, blank=True, null=True)
    status = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'categories'

class Units(models.Model):
    unit_id = models.BigAutoField(primary_key=True)
    unit_name = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'unit'


class Customers(models.Model):
    id = models.BigAutoField(primary_key=True)
    customer_name = models.CharField(max_length=150, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField()
    email = models.CharField(max_length=100, blank=True, null=True)
    place = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'customers'


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.PositiveSmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'



class Products(models.Model):
    id = models.BigAutoField(primary_key=True)
    cat_id = models.BigIntegerField(blank=True, null=True)
    product_name = models.CharField(max_length=150, blank=True, null=True)
    sku = models.CharField(max_length=50, blank=True, null=True)
    unit_id = models.CharField(max_length=50, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    status = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField()
    reorder_level = models.IntegerField(blank=True, null=True)
    stock_qty = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'products'


class Grn(models.Model):
    id = models.BigAutoField(primary_key=True)
    grn_date =  models.DateField(blank=True, null=True)
    po_id = models.BigIntegerField(blank=True, null=True) 
    created_at = models.DateTimeField() 
    status_id = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'grn'


class GRNItems(models.Model):
    id = models.BigAutoField(primary_key=True)
    grn = models.ForeignKey('Grn', models.DO_NOTHING, blank=True, null=True)
    product = models.ForeignKey(Products, models.DO_NOTHING, blank=True, null=True)
    po_qty = models.IntegerField(blank=True, null=True)
    bal_qty = models.IntegerField(blank=True, null=True)
    quantity = models.IntegerField(blank=True, null=True)
    rate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    grn_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    unit = models.ForeignKey(Units, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'grn_items'

class Login(models.Model):
    user_id = models.AutoField(primary_key=True)
    user_name = models.CharField(max_length=100)
    user_type = models.CharField(max_length=50)
    user_status = models.CharField(max_length=20)
    password = models.CharField(max_length=20)

    class Meta:
        managed = False
        db_table = 'login'

class PurchaseOrders(models.Model):
    id = models.BigAutoField(primary_key=True)
    supplier_id = models.BigIntegerField(blank=True, null=True)
    po_date = models.DateField(blank=True, null=True)
    status_id = models.BigIntegerField(blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'purchase_orders'


class PurchaseOrderItems(models.Model):
    id = models.BigAutoField(primary_key=True)
    po = models.ForeignKey('PurchaseOrders', models.DO_NOTHING, blank=True, null=True)
    product = models.ForeignKey(Products, models.DO_NOTHING, blank=True, null=True)
    quantity = models.IntegerField(blank=True, null=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    unit = models.ForeignKey(Units, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'purchase_order_items'

class SaleItems(models.Model):
    id = models.BigAutoField(primary_key=True)
    sale_id = models.BigIntegerField(blank=True, null=True)
    product_id = models.BigIntegerField(blank=True, null=True)
    qty = models.IntegerField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    unit_id = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'sale_items'


class Sales(models.Model):
    id = models.BigAutoField(primary_key=True)
    customer_id = models.BigIntegerField(blank=True, null=True)
    sale_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField()
    status_id = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'sales'


class StockLedger(models.Model):
    id = models.BigAutoField(primary_key=True)
    voucher_type = models.CharField(max_length=30, blank=True, null=True)
    voucher_id = models.BigIntegerField(blank=True, null=True)
    product_id = models.BigIntegerField(blank=True, null=True)
    unit_id = models.BigIntegerField(blank=True, null=True)
    qty = models.IntegerField(blank=True, null=True)
    in_out = models.CharField(max_length=3, blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'stock_ledger'


class StockAdjustment(models.Model):
    id = models.BigAutoField(primary_key=True)
    product_id = models.BigIntegerField(blank=True, null=True)
    qty = models.IntegerField(blank=True, null=True)
    action_type = models.CharField(max_length=10, blank=True, null=True)
    status_id = models.BigIntegerField(blank=True, null=True, default=1)
    reason = models.TextField(blank=True, null=True)
    unit_id = models.BigIntegerField(blank=True, null=True)
    created_at = models.DateTimeField()
    created_by = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'stock_adjustments'


class Suppliers(models.Model):
    id = models.BigAutoField(primary_key=True)
    supplier_name = models.CharField(max_length=150, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=100, blank=True, null=True)    
    place = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'suppliers'


class StockReminder(models.Model):
    id = models.AutoField(primary_key=True)
    staff_id = models.BigIntegerField(blank=True, null=True)
    product_list_summary = models.TextField(blank=True, null=True)
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()
    is_seen = models.IntegerField(default=0)

    class Meta:
        managed = False
        db_table = 'stock_reminders'


class Users(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    email = models.CharField(max_length=100, blank=True, null=True)
    password = models.CharField(max_length=255, blank=True, null=True)
    role = models.CharField(max_length=7, blank=True, null=True)
    status = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'users'
