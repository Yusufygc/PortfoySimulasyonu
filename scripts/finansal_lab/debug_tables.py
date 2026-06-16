"""Sayfadaki tum finansal tablolari ve data-csvname'lerini listele."""
import io, sys, requests
from bs4 import BeautifulSoup
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

TICKER = sys.argv[1] if len(sys.argv) > 1 else "FROTO"
URL = f"https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/sirket-karti.aspx?hisse={TICKER}"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept-Language": "tr-TR,tr"}

r = requests.get(URL, headers=HEADERS, timeout=20)
soup = BeautifulSoup(r.text, "html.parser")
tables = soup.find_all("table")
print(f"Toplam tablo: {len(tables)}\n")

for i, t in enumerate(tables):
    dcsv = t.get("data-csvname", "")
    cls  = " ".join(t.get("class", []))
    selects = t.find_all("select")
    rows = t.find_all("tr")
    sample = ""
    for row in rows[:8]:
        cells = row.find_all(["th", "td"])
        if (len(cells) >= 2
                and not cells[0].find("select")
                and cells[0].get("colspan") not in ("5","4","3","2")):
            txt = cells[0].get_text(strip=True)
            if txt and len(txt) > 3:
                sample = txt[:50]
                break
    if dcsv or selects or "excelexport" in cls:
        print(f"T{i:02d} | csv={dcsv:<18} | cls={cls:<20} | sel={len(selects)} | rows={len(rows):3d} | ornek: {sample!r}")
