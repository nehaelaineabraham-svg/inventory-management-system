import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventory.settings')
django.setup()

def create_table():
    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS purchase_order_items (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                po_id BIGINT,
                product_id BIGINT,
                quantity INT,
                unit_price DECIMAL(10, 2),
                total_price DECIMAL(10, 2),
                FOREIGN KEY (po_id) REFERENCES purchase_orders(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id)
            );
        """)
        print("Table 'purchase_order_items' created or already exists.")

if __name__ == "__main__":
    create_table()
