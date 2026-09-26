import sqlite3

db_path = 'db.sqlite3'
sql_script = 'update_schema.sql'

try:
    with open(sql_script, 'r') as f:
        sql = f.read()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript(sql)
    conn.commit()
    conn.close()
    print("SQL executed successfully.")
except Exception as e:
    print(f"Error: {e}")
