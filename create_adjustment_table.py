import sqlite3
import os

db_path = r'c:\Users\Neha\Desktop\inventory sir with style\db.sqlite3'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS stock_adjustments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id BIGINT,
    qty INTEGER,
    action_type VARCHAR(10),
    status_id BIGINT DEFAULT 1,
    reason TEXT,
    created_at DATETIME,
    created_by BIGINT
)
''')

conn.commit()
conn.close()
print("Table stock_adjustments created successfully.")
