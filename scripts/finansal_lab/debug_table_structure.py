"""
Tablo 20'nin ham HTML yapısını incele — donem parsing için.

Kullanim:
    python scripts/debug_table_structure.py
"""
from __future__ import annotations

import io
import sys
import requests
from bs4 import BeautifulSoup

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

TICKER   = "FROTO"
BASE     = "https://www.isyatirim.com.tr"
PAGE_URL = f"{BASE}/tr-tr/analiz/hisse/Sayfalar/sirket-karti.aspx?hisse={TICKER}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,*/*",
    "Accept-Language": "tr-TR,tr;q=0.9",
}

r = requests.get(PAGE_URL, headers=HEADERS, timeout=20)
soup = BeautifulSoup(r.text, "html.parser")
tables = soup.find_all("table")

TABLE_IDX = 20
t = tables[TABLE_IDX]

print(f"=== Tablo {TABLE_IDX} Ham HTML (ilk 8000 karakter) ===\n")
print(str(t)[:8000])

print(f"\n\n=== Tablo {TABLE_IDX} Satir-Sutun Analizi ===")
rows = t.find_all("tr", recursive=False)
# yoksa:
if not rows:
    rows = t.find_all("tr")

print(f"Toplam satir: {len(rows)}")
for i, row in enumerate(rows[:5]):
    cells = row.find_all(["th", "td"])
    print(f"\n  Satir {i}: {len(cells)} hucre")
    for j, c in enumerate(cells[:8]):
        colspan = c.get("colspan", "1")
        rowspan = c.get("rowspan", "1")
        text = c.get_text(strip=True)[:80]
        print(f"    [{j}] colspan={colspan} rowspan={rowspan}  text='{text}'")
