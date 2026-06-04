import mysql.connector

try:
    conn = mysql.connector.connect(
        host="localhost",
        port=3306,
        user="root",
        password="Suqili20yh",
        database="portfoySim"
    )
    cursor = conn.cursor(dictionary=True)
    
    print("--- Transactions for MERKO ---")
    cursor.execute("SELECT * FROM transactions WHERE symbol LIKE '%MERKO%' ORDER BY date")
    for row in cursor.fetchall():
        print(row)
        
    print("\n--- Corporate Actions for MERKO ---")
    # Check if there is a corporate_actions table or similar
    cursor.execute("SHOW TABLES")
    tables = [list(row.values())[0] for row in cursor.fetchall()]
    print(f"Tables: {tables}")
    
    if 'corporate_actions' in tables:
        cursor.execute("SELECT * FROM corporate_actions WHERE symbol LIKE '%MERKO%' ORDER BY ex_date")
        for row in cursor.fetchall():
            print(row)
            
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals() and conn.is_connected():
        cursor.close()
        conn.close()
