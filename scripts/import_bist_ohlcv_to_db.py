"""
BIST OHLCV CSV dosyalarını stocks + daily_prices tablolarına aktar.

Kaynak dizin: D:\\1KodCalismalari\\Projeler\\VIBE_CODING_UYGULAMA_DENEMELERI\\Merge_PortfoySim\\bist
  - Her ticker ayrı CSV (örn: AKBNK.csv)
  - Başlık: Tarih,Açılış,Yüksek,Düşük,Kapanış,Düzeltilmiş_Kapanış,Hacim
  - Tarih: YYYY-MM-DD ISO
  - close_price kolonu olarak Düzeltilmiş_Kapanış kullanılır (split/temettü temiz)

Idempotent — INSERT ON DUPLICATE KEY UPDATE (upsert_daily_prices_bulk).
Yeniden çalıştırılırsa yalnız yeni satırlar eklenir, mevcutlar güncellenir.

Kullanım:
    python scripts/import_bist_ohlcv_to_db.py [--root <dizin>] [--ticker FROTO] [--dry-run]
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.application.container import AppContainer
from src.domain.models.daily_price import DailyPrice
from src.domain.models.stock import Stock

logger = logging.getLogger(__name__)

_DEFAULT_ROOT = Path(
    r"D:\1KodCalismalari\Projeler\VIBE_CODING_UYGULAMA_DENEMELERI\Merge_PortfoySim\bist"
)

# CSV TR başlık → standart isim
_COL_DATE  = "Tarih"
_COL_CLOSE = "Düzeltilmiş_Kapanış"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="BIST OHLCV CSV → MySQL importer.")
    p.add_argument("--root", type=Path, default=_DEFAULT_ROOT,
                   help=f"CSV kök dizini (varsayılan: {_DEFAULT_ROOT})")
    p.add_argument("--ticker", help="Sadece tek ticker import et (test için)")
    p.add_argument("--dry-run", action="store_true",
                   help="DB'ye yazmadan sadece say ve doğrula")
    p.add_argument("--limit", type=int, default=0,
                   help="İşlenecek max CSV sayısı (0 = hepsi)")
    return p.parse_args()


def _read_csv(path: Path) -> pd.DataFrame | None:
    """CSV'yi oku, kapanış sütununu seç, NaN/negatif/sıfır temizle."""
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except Exception as exc:
        logger.warning("Okunamadı [%s]: %s", path.name, exc)
        return None
    if _COL_DATE not in df.columns or _COL_CLOSE not in df.columns:
        logger.warning("Eksik kolon [%s]: %s", path.name, list(df.columns))
        return None
    df = df[[_COL_DATE, _COL_CLOSE]].copy()
    df.columns = ["price_date", "close"]
    df["price_date"] = pd.to_datetime(df["price_date"], errors="coerce").dt.date
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["price_date", "close"])
    df = df[df["close"] > 0]
    return df if not df.empty else None


def _ensure_stock(stock_repo, ticker: str) -> int:
    """stocks tablosunda ticker varsa id'sini döndür, yoksa ekle."""
    existing = stock_repo.get_stock_by_ticker(ticker)
    if existing is not None:
        return int(existing.id)
    created = stock_repo.insert_stock(Stock(id=None, ticker=ticker, name=None, currency_code="TRY"))
    logger.info("stocks tablosuna eklendi: %s (id=%d)", ticker, created.id)
    return int(created.id)


def _df_to_daily_prices(df: pd.DataFrame, stock_id: int) -> list[DailyPrice]:
    out: list[DailyPrice] = []
    for row in df.itertuples(index=False):
        try:
            out.append(DailyPrice(
                id=None,
                stock_id=stock_id,
                price_date=row.price_date,
                close_price=Decimal(str(row.close)),
                currency_code="TRY",
                source="bist_csv",
            ))
        except (ValueError, ArithmeticError) as exc:
            logger.debug("Geçersiz fiyat satırı atlandı: %s", exc)
    return out


def _import_csv(path: Path, container, dry_run: bool) -> tuple[int, int]:
    """Tek CSV'yi import et. Dönüş: (stock_id, eklenen satır sayısı)."""
    ticker = path.stem.strip().upper()
    df = _read_csv(path)
    if df is None or df.empty:
        return 0, 0

    if dry_run:
        return 0, len(df)

    stock_id = _ensure_stock(container.stock_repo, ticker)
    prices = _df_to_daily_prices(df, stock_id)
    container.price_repo.upsert_daily_prices_bulk(prices)
    return stock_id, len(prices)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    args = _parse_args()

    if not args.root.exists() or not args.root.is_dir():
        logger.error("Kök dizin yok: %s", args.root)
        sys.exit(1)

    pattern = f"{args.ticker.upper()}.csv" if args.ticker else "*.csv"
    csv_files = sorted(args.root.glob(pattern))
    if args.limit > 0:
        csv_files = csv_files[: args.limit]

    if not csv_files:
        logger.error("CSV bulunamadı (pattern=%s)", pattern)
        sys.exit(1)

    logger.info("İşlenecek CSV sayısı: %d (dry_run=%s)", len(csv_files), args.dry_run)
    container = AppContainer()

    total_tickers = 0
    total_rows    = 0
    failures      = 0

    for i, path in enumerate(csv_files, start=1):
        try:
            stock_id, n_rows = _import_csv(path, container, args.dry_run)
            if n_rows > 0:
                total_tickers += 1
                total_rows    += n_rows
            if i % 20 == 0 or i == len(csv_files):
                logger.info(
                    "  ilerleme %d/%d  son=%s  toplam_ticker=%d  toplam_satır=%d",
                    i, len(csv_files), path.stem, total_tickers, total_rows,
                )
        except Exception:
            failures += 1
            logger.exception("Import hatası [%s]", path.name)

    logger.info(
        "Tamamlandı: %d ticker, %d satır, %d hata.",
        total_tickers, total_rows, failures,
    )


if __name__ == "__main__":
    main()
