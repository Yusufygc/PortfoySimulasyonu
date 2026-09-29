import sqlite3

conn = sqlite3.connect('data/portfolio.db')
cursor = conn.cursor()
tables = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print(f"Toplam Tablo Sayisi: {len(tables)}")

counts = {}
for t in tables:
    if not t.startswith("sqlite_"):
        try:
            cnt = cursor.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            counts[t] = cnt
        except Exception as e:
            counts[t] = str(e)

for t, c in sorted(counts.items(), key=lambda x: str(x[0])):
    print(f"  {t}: {c} kayit")
