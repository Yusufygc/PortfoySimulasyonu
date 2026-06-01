import sys
import os
from datetime import date
from decimal import Decimal
from pathlib import Path

# Add project root to python path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from config.settings_loader import load_settings
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import ORMDailyPrice

def main():
    print("=" * 60)
    print("  Veritabanı Hatalı Fiyat Düzeltme İşlemi (2026-06-01)")
    print("=" * 60)

    config = load_settings()
    engine_provider = SQLAlchemyEngineProvider(config)

    with engine_provider.get_session() as session:
        # MERKO.IS (stock_id = 47)
        merko_price = session.query(ORMDailyPrice).filter_by(stock_id=47, price_date=date(2026, 6, 1)).first()
        if merko_price:
            old_val = merko_price.close_price
            merko_price.close_price = Decimal("2.0400")
            print(f"MERKO.IS (2026-06-01) guncellendi: {old_val} -> {merko_price.close_price}")
        else:
            print("MERKO.IS icin 2026-06-01 tarihli kayit bulunamadi.")

        # RUZYE.IS (stock_id = 42)
        ruzye_price = session.query(ORMDailyPrice).filter_by(stock_id=42, price_date=date(2026, 6, 1)).first()
        if ruzye_price:
            old_val = ruzye_price.close_price
            ruzye_price.close_price = Decimal("11.9500")
            print(f"RUZYE.IS (2026-06-01) guncellendi: {old_val} -> {ruzye_price.close_price}")
        else:
            print("RUZYE.IS icin 2026-06-01 tarihli kayit bulunamadi.")

        try:
            session.commit()
            print("\n[OK] Veritabanı basariyla guncellendi ve commitleme tamamlandi.")
        except Exception as e:
            session.rollback()
            print(f"\n[HATA] Guncelleme sirasinda hata olustu, islem geri alindi (rollback): {e}")

    print("=" * 60)

if __name__ == "__main__":
    main()
