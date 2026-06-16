"""T20 (malitablo) icindeki section header'lari ve satir yapisini incele."""
import io, sys, requests
from bs4 import BeautifulSoup
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

TICKER = sys.argv[1] if len(sys.argv) > 1 else "FROTO"
URL = f"https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/sirket-karti.aspx?hisse={TICKER}"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept-Language": "tr-TR,tr"}

r = requests.get(URL, headers=HEADERS, timeout=20)
soup = BeautifulSoup(r.text, "html.parser")
t20 = soup.find("table", attrs={"data-csvname": "malitablo"})

rows = t20.find_all("tr")
print(f"T20 toplam satir: {len(rows)}\n")
print("Satir analizi (colspan=5 = section baslik, diger = veri):\n")
for i, row in enumerate(rows):
    cells = row.find_all(["th", "td"])
    if not cells:
        continue
    first = cells[0]
    colspan = first.get("colspan", "1")
    has_select = bool(first.find("select"))
    text = first.get_text(strip=True)[:60]
    if has_select:
        print(f"  [{i:3d}] SELECT HEADER")
    elif colspan in ("5", "4", "3"):
        print(f"  [{i:3d}] SECTION [{colspan}]: {text!r}")
    elif len(cells) >= 2:
        val = cells[1].get_text(strip=True)[:20]
        print(f"  [{i:3d}] veri: {text:<45} | {val}")
    else:
        print(f"  [{i:3d}] tekli: {text!r}")

# T05 yapisi
t05 = soup.find_all("table")[5]
print(f"\n\n--- T05 HTML (ilk 2000 karakter) ---")
print(str(t05)[:2000])
