from django.db import connection

query = """
CREATE TABLE IF NOT EXISTS stock_adjustments (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    product_id BIGINT,
    qty INT,
    action_type VARCHAR(10),
    status_id BIGINT DEFAULT 1,
    reason TEXT,
    created_at DATETIME,
    created_by BIGINT
)
"""

with connection.cursor() as cursor:
    cursor.execute(query)

print("Table stock_adjustments created successfully in MySQL.")
