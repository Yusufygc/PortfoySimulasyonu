"""Hisse detayı eylemleri: emir gönderme ve Excel raporu (arka plan iş parçacığında çalışır)."""
from __future__ import annotations

from datetime import date, datetime, time as dt_time
from decimal import Decimal
import logging
from pathlib import Path

from src.application.services.portfolio.trade_entry_service import TradeRequest
from src.domain.models.trade import TradeSide
from src.ui_qml.messages import msg
from src.ui_qml.presenters.formatting import tr_number, tr_pct

logger = logging.getLogger(__name__)


def _trade_failure_text(exc: Exception) -> str:
    """`ValueError` kullanıcıya yönelik doğrulama iletisidir (seans, nakit, lot); diğer istisna metinleri sızdırılmaz."""
    if isinstance(exc, ValueError):
        return msg("stock_detail.emir_iletilemedi_neden", exc=exc)
    return msg("stock_detail.emir_iletilemedi")


class StockDetailActionsMixin:
    def _execute_trade_worker(self, side: str, qty: int, price: float, tr_date: date, tr_time: dt_time) -> None:
        """Alım/satım işlemini veritabanında kaydeder."""
        try:
            is_buy = side.upper() == "BUY" or side.upper() == "ALIM"
            tr_side = TradeSide.BUY if is_buy else TradeSide.SELL

            if self._context_type == "model" and self._context_id > 0:
                model_service = getattr(self._container, "model_portfolio_service", None) if self._container else None
                if not model_service:
                    raise RuntimeError(msg("stock_detail.model_portfoy_servisi_bulunamadi"))
                from src.application.services.planning.model_portfolio_trade_service import ModelTradeInput
                model_service.add_trade_by_ticker(
                    portfolio_id=self._context_id,
                    ticker=self._ticker,
                    trade_input=ModelTradeInput(
                        side="BUY" if is_buy else "SELL",
                        quantity=qty,
                        price=Decimal(str(price)),
                        trade_date=tr_date,
                        trade_time=tr_time,
                    ),
                )
                total_amount = qty * price
                action_tr = msg("stock_detail.satin_alindi") if is_buy else msg("stock_detail.satildi")
                text = msg("stock_detail.adet_model_portfoye", qty=qty, ticker=self._ticker, action_tr=action_tr, total_amount=tr_number(total_amount))
                self._asyncTradeResult.emit(True, text)
                return

            trade_entry_service = getattr(self._container, "trade_entry_service", None) if self._container else None
            if not trade_entry_service:
                raise RuntimeError(msg("stock_detail.islem_giris_servisi_bulunamadi"))

            # Seans/nakit/lot doğrulamaları TradeEntryService içinde yapılır (Dashboard ile aynı yol).
            trade_entry_service.submit_trade(
                TradeRequest(
                    ticker=self._raw_ticker or self._ticker,
                    side=tr_side,
                    quantity=qty,
                    price=Decimal(str(price)),
                    trade_date=tr_date,
                    trade_time=tr_time,
                    name=self._company_name or None,
                )
            )
            total_amount = qty * price
            action_tr = msg("stock_detail.satin_alindi") if is_buy else msg("stock_detail.satildi")
            text = msg("stock_detail.adet_basariyla", qty=qty, ticker=self._ticker, action_tr=action_tr, total_amount=tr_number(total_amount))
            self._asyncTradeResult.emit(True, text)

        except Exception as e:
            logger.exception("Emir iletim hatası (%s): %s", self._ticker, e)
            self._asyncTradeResult.emit(False, _trade_failure_text(e))

    def _export_excel_worker(self) -> None:
        """Bu hissenin işlem dökümünü ve pozisyon özetini Excel olarak kaydeder."""
        try:
            import pandas as pd
            desktop = Path.home() / "Desktop"
            out_dir = desktop if desktop.exists() else Path("reports").resolve()
            out_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target_file = out_dir / f"Hisse_Detay_{self._ticker}_{timestamp}.xlsx"

            # 1. Pozisyon Özeti DataFrame
            summary_data = [
                {msg("stock_detail.metric"): msg("stock_detail.ticker_label"), msg("stock_detail.deger"): self._ticker},
                {msg("stock_detail.metric"): msg("stock_detail.sirket_adi"), msg("stock_detail.deger"): self._company_name},
                {msg("stock_detail.metric"): msg("stock_detail.sektor"), msg("stock_detail.deger"): self._sector},
                {msg("stock_detail.metric"): msg("stock_detail.portfoy"), msg("stock_detail.deger"): self._portfolio_name},
                {msg("stock_detail.metric"): msg("stock_detail.report_date"), msg("stock_detail.deger"): datetime.now().strftime("%d.%m.%Y %H:%M")},
                {msg("stock_detail.metric"): msg("stock_detail.current_lots"), msg("stock_detail.deger"): self._quantity},
                {msg("stock_detail.metric"): msg("stock_detail.avg_cost_tl"), msg("stock_detail.deger"): self._avg_cost},
                {msg("stock_detail.metric"): msg("stock_detail.son_kapanis_fiyati_tl"), msg("stock_detail.deger"): self._current_price},
                {msg("stock_detail.metric"): msg("stock_detail.toplam_piyasa_degeri_tl"), msg("stock_detail.deger"): self._market_value},
                {msg("stock_detail.metric"): msg("stock_detail.net_pnl_tl"), msg("stock_detail.deger"): self._unrealized_pnl},
                {msg("stock_detail.metric"): msg("stock_detail.kar_zarar_orani"), msg("stock_detail.deger"): tr_pct(self._unrealized_pnl_pct)},
                {msg("stock_detail.metric"): msg("stock_detail.portfoy_agirligi"), msg("stock_detail.deger"): f"%{tr_number(self._portfolio_weight_pct, 1)}"},
            ]
            df_summary = pd.DataFrame(summary_data)

            # 2. İşlem Geçmişi DataFrame
            trades_export = []
            for t in self._trades_list:
                trades_export.append({
                    "Tarih": t.get("date", "-"),
                    "Saat": t.get("time", "-"),
                    msg("stock_detail.islem_turu"): t.get("side", "-"),
                    "Adet (Lot)": t.get("quantity", 0),
                    "Fiyat (TL)": t.get("price", 0.0),
                    "Toplam Tutar (TL)": t.get("total", 0.0),
                })
            df_trades = pd.DataFrame(trades_export) if trades_export else pd.DataFrame([{msg("stock_detail.info"): msg("stock_detail.kayitli_islem_bulunamadi")}])

            # 3. Sermaye Artırımları DataFrame
            corp_export = []
            for c in self._corp_actions_list:
                corp_export.append({
                    "Tarih": c.get("date", "-"),
                    msg("stock_detail.islem_turu"): c.get("actionType", "-"),
                    msg("stock_detail.artirim_orani"): c.get("ratioStr", "-"),
                    msg("stock_detail.uygulandi_mi"): msg("stock_detail.yes") if c.get("applied") else msg("stock_detail.hayir"),
                })
            df_corp = pd.DataFrame(corp_export) if corp_export else pd.DataFrame([{msg("stock_detail.info"): msg("stock_detail.kayitli_sermaye_artirimi_bulunamadi")}])

            with pd.ExcelWriter(str(target_file), engine="openpyxl") as writer:
                df_summary.to_excel(writer, sheet_name=msg("stock_detail.pozisyon_ozeti"), index=False)
                df_trades.to_excel(writer, sheet_name=msg("stock_detail.islem_gecmisi"), index=False)
                df_corp.to_excel(writer, sheet_name=msg("stock_detail.sermaye_artirimlari"), index=False)

                # Formatter mevcutsa profesyonel stilleri uygula
                formatter = getattr(self._container, "excel_formatter", None) if self._container else None
                if formatter:
                    try:
                        formatter.apply_formatting(writer, msg("stock_detail.pozisyon_ozeti"), df_summary)
                        formatter.apply_formatting(writer, msg("stock_detail.islem_gecmisi"), df_trades)
                        formatter.apply_formatting(writer, msg("stock_detail.sermaye_artirimlari"), df_corp)
                    except Exception as fe:
                        logger.debug("ExcelFormatter opsiyonel stil uygulanamadı: %s", fe)

            text = msg("stock_detail.detay_raporu_basariyla_kaydedildi", ticker=self._ticker, name=target_file.name)
            self._asyncExportResult.emit(True, text)

        except Exception as e:
            logger.exception("Excel hisse dökümü hatası: %s", e)
            self._asyncExportResult.emit(False, msg("stock_detail.excel_raporu_olusturulamadi", e=e))
