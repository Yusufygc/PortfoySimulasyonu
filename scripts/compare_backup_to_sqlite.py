import re
import sqlite3
from collections import defaultdict

# 1. Parse portfoysim.sql table insert counts
sql_counts = defaultdict(int)
current_table = None

with open('backups/mysql/portfoysim.sql', 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        m = re.match(r"INSERT INTO `(\w+)` VALUES", line)
        if m:
            table = m.group(1)
            # count the number of rows inserted in this statement
            # usually: (...),(...),(...)
            # A rough estimate or accurate count by counting '),('
            row_count = line.count("),(") + 1
            sql_counts[table] += row_count

print("=== PORTFOYSIM.SQL (Yedek) ===")
for t, cnt in sorted(sql_counts.items()):
    print(f"  {t}: ~{cnt} kayit")

# 2. Compare with SQLite
conn = sqlite3.connect('data/portfolio.db')
c = conn.cursor()
print("\n=== DATA/PORTFOLIO.DB (Mevcut SQLite) ===")
sqlite_tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
for t in sorted(sqlite_tables):
    if not t.startswith("sqlite_"):
        cnt = c.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        backup_cnt = sql_counts.get(t, 0)
        match_str = "[ESIT]" if cnt == backup_cnt else f"[FARK] (Yedek: {backup_cnt}, SQLite: {cnt})"
        print(f"  {t:30}: SQLite={cnt:6} | {match_str}")
