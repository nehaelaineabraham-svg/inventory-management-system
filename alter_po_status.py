import os
import sys
import django

sys.path.insert(0, r'D:\inventory')
os.environ['DJANGO_SETTINGS_MODULE'] = 'inventory.settings'
django.setup()

from django.db import connection

c = connection.cursor()

sql = "ALTER TABLE purchase_orders MODIFY COLUMN status ENUM('PENDING','APPROVED','REJECTED','RECEIVED') DEFAULT 'PENDING'"
c.execute(sql)
print("SUCCESS: purchase_orders.status column altered to ENUM")

c.execute("SELECT DISTINCT status FROM purchase_orders")
print("Current status values in DB:", c.fetchall())
