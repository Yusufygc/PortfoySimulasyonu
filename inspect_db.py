import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

conn = mysql.connector.connect(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", 3306)),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "portfoySim")
)

cursor = conn.cursor(dictionary=True)

print("\n--- BORSK Daily Prices ---")
cursor.execute("SELECT * FROM daily_prices WHERE stock_id = 68 ORDER BY price_date DESC LIMIT 5")
prices = cursor.fetchall()
for row in prices:
    print(row)
if not prices:
    print("NO PRICES FOUND FOR BORSK!")
