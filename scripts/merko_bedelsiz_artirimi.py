"""
MERKO.IS bedelsiz sermaye artırımı onarım scripti.

Ex-date : 2026-05-05
Oran    : %638,33834
Kaynak  : KAP Bildirim 1603760

Ön koşul:
    scripts/alter_corporate_actions_price_adjustment.sql mevcut DB'de çalıştırılmış olmalı.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from decimal import Decimal

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.application.container import AppContainer
from src.domain.models.corporate_action import ActionType
from src.domain.models.position import Position


TICKER = "MERKO.IS"
EX_DATE = date(2026, 5, 5)
REF_DATE = date(2026, 5, 4)
RATIO_PCT = Decimal("638.33834")
RATIO = Decimal("6.3833834")
NOTES = "KAP Bildirim 1603760: %638,33834 bedelsiz sermaye artırımı, ex-date 05.05.2026"
RATIO_TOLERANCE = Decimal("0.0001")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MERKO.IS bedelsiz sermaye artırımı onarımı")
    parser.add_argument("--dry-run", action="store_true", help="DB'ye yazmadan yapılacak işlemi gösterir")
    return parser.parse_args()


def _find_existing_merko_action(container: AppContainer, stock_id: int):
    for action in container.corporate_action_service.get_by_stock(stock_id):
        if action.action_type != ActionType.BEDELSIZ:
            continue
        if action.ex_date != EX_DATE:
            continue
        if _same_ratio(action.ratio, RATIO):
            return action
    return None


def _same_ratio(left: Decimal, right: Decimal) -> bool:
    return abs(left - right) <= RATIO_TOLERANCE


def _print_position(container: AppContainer, stock_id: int) -> Position:
    trades = container.portfolio_repo.get_trades_by_stock(stock_id)
    position = Position.from_trades(stock_id, trades)
    if position.total_quantity == 0:
        raise RuntimeError("Portföyde MERKO.IS pozisyonu yok.")

    new_shares = int(Decimal(str(position.total_quantity)) * RATIO)
    new_quantity = position.total_quantity + new_shares
    new_avg = position.total_cost / Decimal(str(new_quantity))

    print(f"  Mevcut lot       : {position.total_quantity:,}")
    print(f"  Yeni bedelsiz lot: {new_shares:,}")
    print(f"  Toplam lot       : {new_quantity:,}")
    print(f"  Ort. maliyet     : {position.average_cost:.4f} -> {new_avg:.4f} TL")
    return position


def _print_current_position(container: AppContainer, stock_id: int) -> Position:
    trades = container.portfolio_repo.get_trades_by_stock(stock_id)
    position = Position.from_trades(stock_id, trades)
    if position.total_quantity == 0:
        raise RuntimeError("Portföyde MERKO.IS pozisyonu yok.")
    print(f"  Mevcut lot       : {position.total_quantity:,}")
    print(f"  Ort. maliyet     : {position.average_cost:.4f} TL")
    print(f"  Toplam maliyet   : {position.total_cost:.2f} TL")
    return position


def _reference_price(container: AppContainer, stock_id: int):
    daily = container.price_repo.get_price_for_date(stock_id, REF_DATE)
    if daily is None:
        print(f"  Uyarı: {REF_DATE} fiyatı DB'de yok; teorik baz fiyat gösterimi atlanacak.")
        return None
    theoretical = Decimal(str(daily.close_price)) / (Decimal("1") + RATIO)
    print(f"  Referans fiyat   : {daily.close_price:.4f} TL ({REF_DATE})")
    print(f"  Teorik baz fiyat : {theoretical:.4f} TL")
    return Decimal(str(daily.close_price))


def main() -> int:
    args = _parse_args()
    print("=" * 72)
    print(f"MERKO.IS bedelsiz sermaye artırımı onarımı - %{RATIO_PCT}")
    print("=" * 72)

    container = AppContainer()
    stock = container.stock_repo.get_stock_by_ticker(TICKER)
    if stock is None or stock.id is None:
        raise RuntimeError(f"{TICKER} veritabanında bulunamadı.")

    print(f"  Hisse            : {stock.ticker} (stock_id={stock.id})")
    print(f"  Ex-date          : {EX_DATE}")
    print(f"  Oran             : {RATIO} (%{RATIO_PCT})")

    existing = _find_existing_merko_action(container, stock.id)
    if existing is not None and existing.applied:
        print(f"  Durum            : mevcut action_id={existing.id}, applied=True, prices_adjusted={existing.prices_adjusted}")
        _print_current_position(container, stock.id)
        if args.dry_run:
            if existing.prices_adjusted:
                print("  DRY RUN          : işlem gerekmiyor.")
            else:
                print("  DRY RUN          : sentetik trade açılmadan sadece geçmiş fiyatlar düzeltilecek.")
            return 0

        adjustment = container.corporate_action_service.adjust_prices_for_action(existing.id)
        if adjustment.already_adjusted:
            print(f"  Fiyat düzeltme   : zaten uygulanmış, factor={adjustment.factor}")
        else:
            print(f"  Fiyat düzeltme   : {adjustment.adjusted_count} kayıt, factor={adjustment.factor}")
        return 0

    ref_price = _reference_price(container, stock.id)
    _print_position(container, stock.id)

    if existing is None:
        print("  Durum            : MERKO action kaydı bulunamadı; yeni kayıt oluşturulacak.")
        if args.dry_run:
            print("  DRY RUN          : register_bedelsiz + apply_action çalıştırılmadı.")
            return 0
        action = container.corporate_action_service.register_bedelsiz(
            stock_id=stock.id,
            ex_date=EX_DATE,
            ratio=RATIO,
            notes=NOTES,
        )
        result = container.corporate_action_service.apply_action(
            action_id=action.id,
            current_price=ref_price,
        )
        print(f"  Uygulandı        : action_id={action.id}")
        print(f"  Fiyat düzeltme   : {result.price_adjustment_count} kayıt, factor={result.price_adjustment_factor}")
        return 0

    print(f"  Durum            : mevcut action_id={existing.id}, applied={existing.applied}, prices_adjusted={existing.prices_adjusted}")
    if args.dry_run:
        print("  DRY RUN          : mevcut action portföye uygulanacak ve fiyatlar düzeltilecek.")
        return 0

    result = container.corporate_action_service.apply_action(
        action_id=existing.id,
        current_price=ref_price,
    )
    print(f"  Uygulandı        : {result.shares_before:,} -> {result.shares_after:,} lot")
    print(f"  Fiyat düzeltme   : {result.price_adjustment_count} kayıt, factor={result.price_adjustment_factor}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
