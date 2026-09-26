from inventory import models
from django.db.models import Sum, Case, When, F, Value, IntegerField
from django.db.models.functions import Coalesce
import datetime

def alerts_processor(request):
    try:
        # Check Low Stock (Current Stock < Reorder Level (10))
        from django.db import connection
        
        cursor = connection.cursor()
        
        # Low Stock Alert
        cursor.execute("""
            SELECT 
                p.product_name,
                (COALESCE(SUM(CASE WHEN sl.in_out = 'IN' THEN sl.qty ELSE 0 END), 0) - 
                 COALESCE(SUM(CASE WHEN sl.in_out = 'OUT' THEN sl.qty ELSE 0 END), 0)) as current_stock,
                 p.reorder_level
            FROM products p
            LEFT JOIN stock_ledger sl ON p.id = sl.product_id
            GROUP BY p.id, p.product_name, p.reorder_level
            HAVING current_stock < p.reorder_level
        """)
        low_stock_items = cursor.fetchall()
        
        # New Reminders from Staff
        cursor.execute("SELECT COUNT(*) FROM stock_reminders WHERE is_seen = 0")
        unread_reminders_count = cursor.fetchone()[0]
        
        return {
            'low_stock_count': len(low_stock_items),
            'low_stock_items': low_stock_items,
            'unread_reminders_count': unread_reminders_count,
            'expiry_count': 0,
            'expiry_items': []
        }
    except Exception as e:
        # Fail silently to avoid breaking pages if logic errs
        print(f"Alerts Error: {e}")
        return {
            'low_stock_count': 0, 
            'expiry_count': 0
        }
