import MySQLdb
import sys

print("Testing MySQL connection...")

try:
    print("Attempting to connect to localhost...")
    conn = MySQLdb.connect(host="localhost", user="root", passwd="", db="invent", port=3306)
    print("SUCCESS: Connected to localhost!")
    conn.close()
except Exception as e:
    print(f"FAILURE: Could not connect to localhost: {e}")

try:
    print("\nAttempting to connect to 127.0.0.1...")
    conn = MySQLdb.connect(host="127.0.0.1", user="root", passwd="", db="invent", port=3306)
    print("SUCCESS: Connected to 127.0.0.1!")
    conn.close()
except Exception as e:
    print(f"FAILURE: Could not connect to 127.0.0.1: {e}")
