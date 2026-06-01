# src/ui/pages/comparison/utils/comparison_data_manager.py
"""Karşılaştırma sayfasının veri ve filtre yönetimi."""
from __future__ import annotations

import logging
from datetime import date
from typing import TYPE_CHECKING

import pandas as pd
from PyQt5.QtCore import QThreadPool

from src.ui.worker import Worker
from src.application.services.analysis.models import AnalysisFilterState
from src.application.services.analysis.comparison_service import ComparisonService

if TYPE_CHECKING:
    from src.ui.pages.comparison.comparison_page import ComparisonPage

logger = logging.getLogger(__name__)


class ComparisonDataManager:
    """
    Varlık listelerini yükler, tarih uyarılarını üretir,
    Worker'ları başlatır ve DTO verilerini DataFrame'e dönüştürür.
    """

    def __init__(self, page: ComparisonPage, analysis_service) -> None:
        self.page = page
        self.analysis_service = analysis_service
        self.threadpool = QThreadPool.globalInstance()

    # ------------------------------------------------------------------
    # Varlık seçeneklerini yükleme
    # ------------------------------------------------------------------

    def get_current_base_assets(self) -> list[tuple[str, str]]:
        """Tüm portföy, benchmark ve çözümlenmiş hisse seçeneklerini döner."""
        assets: list[tuple[str, str]] = []
        page = self.page

        if not hasattr(page, "_asset_labels"):
            page._asset_labels = {}

        portfolios = self.analysis_service.get_portfolio_options()
        for p in portfolios:
            assets.append((p.label, p.code))
            assets.append((f"{p.label} + Hisseleri", f"holdings:{p.code}"))
            page._asset_labels[p.code] = p.label
            page._asset_labels[f"holdings:{p.code}"] = f"{p.label} + Hisseleri"

        benchmarks = self.analysis_service.get_benchmark_definitions()
        for b in benchmarks:
            assets.append((b.label, b.code))
            page._asset_labels[b.code] = b.label

        for code, label in page._asset_labels.items():
            if code.isdigit() and not any(item[1] == code for item in assets):
                assets.append((label, code))

        page._base_assets_cache = assets
        return assets

    def load_initial_options(self) -> None:
        """Ribbon bar'ı başlangıç seçenekleriyle doldurur."""
        page = self.page
        page._asset_labels = {}
        assets = self.get_current_base_assets()
        page.ribbon_bar.set_assets(assets)
        self.refresh_panel_options()

    def refresh_panel_options(self) -> None:
        """Her grafik panelinin portföy override menüsünü günceller."""
        page = self.page
        portfolio_choices = [
            (p.label, p.code)
            for p in self.analysis_service.get_portfolio_options()
        ]
        panel_keys = [
            ("main_chart_panel",    "main_chart"),
            ("summary_table_panel", "summary_table"),
            ("drawdown_chart_panel","drawdown_chart"),
            ("periodic_chart_panel","periodic_chart"),
            ("scatter_chart_panel", "scatter_chart"),
            ("treemap_chart_panel", "treemap_chart"),
        ]
        for panel_attr, chart_key in panel_keys:
            panel = getattr(page, panel_attr, None)
            if panel is None:
                continue
            panel.update_portfolio_options(
                portfolio_choices,
                page.chart_overrides.get(chart_key),
                lambda code, ck=chart_key: self.handle_chart_portfolio_selected(ck, code),
            )

    # ------------------------------------------------------------------
    # Override mantığı
    # ------------------------------------------------------------------

    def handle_chart_portfolio_selected(
        self, chart_key: str, portfolio_code: str | None
    ) -> None:
        """Belirli bir grafik için portföy override'ı ayarlar veya sıfırlar."""
        page = self.page
        page.chart_overrides[chart_key] = portfolio_code
        self.refresh_panel_options()

        if portfolio_code is None:
            if page.last_global_df is not None:
                mode = page.ribbon_bar.selected_mode()
                if chart_key == "main_chart":
                    page._renderer.render_main_chart(page.last_global_df)
                else:
                    df_metrics = page.last_global_df
                    if mode == "Rasyo Modu":
                        num_code, den_code = page.ribbon_bar.ratio_assets()
                        num_col = self.find_column_by_code(page.last_global_df, num_code)
                        den_col = self.find_column_by_code(page.last_global_df, den_code)
                        if num_col and den_col:
                            ratio_series = ComparisonService.calculate_asset_ratio(
                                page.last_global_df[num_col],
                                page.last_global_df[den_col],
                            )
                            df_metrics = pd.DataFrame(
                                {f"{num_col} / {den_col}": ratio_series}
                            )
                    page._renderer.render_single_chart(chart_key, df_metrics)
        else:
            self._request_override_refresh(chart_key, portfolio_code)

    def _request_override_refresh(self, chart_key: str, portfolio_code: str) -> None:
        """Belirli bir grafik için özel veri çeker."""
        page = self.page
        start_date, end_date = page.ribbon_bar.date_range()
        try:
            stock_map = self.analysis_service.get_stock_map_for_source(portfolio_code)
            stock_ids = list(stock_map.keys())
            for sid, ticker in stock_map.items():
                page._asset_labels[str(sid)] = ticker

            filter_state = AnalysisFilterState(
                start_date=start_date,
                end_date=end_date,
                selected_stock_ids=stock_ids,
                selected_benchmarks=[],
                portfolio_source=portfolio_code,
                comparison_portfolio_sources=[portfolio_code],
                currency_mode="TL",
            )
            page._request_seq += 1
            request_id = page._request_seq
            worker = Worker(self.analysis_service.get_comparison_view, filter_state)
            worker.signals.result.connect(
                lambda result, rid=request_id, ck=chart_key, pc=portfolio_code:
                    self._on_override_data_ready(rid, ck, pc, result)
            )
            worker.signals.error.connect(
                lambda err: logger.error("Error fetching override data: %s", err)
            )
            self.threadpool.start(worker)
        except Exception as exc:
            logger.error("Error in override refresh for %s: %s", chart_key, exc, exc_info=True)

    def _on_override_data_ready(
        self, request_id: int, chart_key: str, portfolio_code: str, dto
    ) -> None:
        """Override veri isteği tamamlandığında çağrılır."""
        page = self.page
        if page.chart_overrides.get(chart_key) != portfolio_code:
            return

        series_dict: dict[str, pd.Series] = {}

        if dto.portfolio_series:
            p_series = pd.Series(
                {pd.Timestamp(d): float(v) for d, v in dto.portfolio_series.items()}
            )
            p_series.name = dto.current_portfolio_label
            series_dict[dto.current_portfolio_label] = p_series
            page.code_to_label[portfolio_code] = dto.current_portfolio_label
            page.code_to_label[f"portfolio:{portfolio_code}"] = dto.current_portfolio_label

        for cp in dto.comparison_portfolios:
            if cp.points:
                s = pd.Series({pd.Timestamp(d): float(v) for d, v in cp.points.items()})
                s.name = cp.label
                series_dict[cp.label] = s
                page.code_to_label[cp.code] = cp.label
                page.code_to_label[f"portfolio:{cp.code}"] = cp.label

        for stock_id, points in dto.stock_series.items():
            if points:
                s = pd.Series({pd.Timestamp(d): float(v) for d, v in points.items()})
                s.name = page._asset_labels.get(str(stock_id), str(stock_id))
                series_dict[s.name] = s

        if not series_dict:
            return

        aligned_df = ComparisonService.align_financial_series(series_dict)
        mode = page.ribbon_bar.selected_mode()

        if chart_key == "main_chart":
            page._renderer.render_main_chart(aligned_df)
        else:
            df_metrics = aligned_df
            if mode == "Rasyo Modu":
                num_code, den_code = page.ribbon_bar.ratio_assets()
                num_col = self.find_column_by_code(aligned_df, num_code)
                den_col = self.find_column_by_code(aligned_df, den_code)
                if num_col and den_col:
                    ratio_series = ComparisonService.calculate_asset_ratio(
                        aligned_df[num_col], aligned_df[den_col]
                    )
                    df_metrics = pd.DataFrame({f"{num_col} / {den_col}": ratio_series})
            page._renderer.render_single_chart(chart_key, df_metrics)

    # ------------------------------------------------------------------
    # Tarih doğrulama
    # ------------------------------------------------------------------

    def check_date_warnings(self) -> list[str]:
        """Seçili tarihlere ilişkin doğrulama uyarıları döner."""
        page = self.page
        warnings: list[str] = []
        start_date, end_date = page.ribbon_bar.date_range()

        if start_date > end_date:
            warnings.append("Başlangıç tarihi bitiş tarihinden sonra olamaz.")
            return warnings

        if end_date > date.today():
            warnings.append("Bitiş tarihi bugünden ileri bir tarih olamaz.")

        selected_codes = page.ribbon_bar.selected_assets()
        for code in selected_codes:
            if code == "dashboard" or code.startswith("portfolio:") or code.startswith("model:"):
                try:
                    first_trade_dt = self.analysis_service.get_first_trade_date_for_source(code)
                    if first_trade_dt and start_date < first_trade_dt:
                        label = getattr(page, "_asset_labels", {}).get(code, code)
                        warnings.append(
                            f"Seçilen başlangıç tarihi ({start_date.strftime('%d.%m.%Y')}), "
                            f"<b>{label}</b> varlığının ilk işlem tarihinden "
                            f"({first_trade_dt.strftime('%d.%m.%Y')}) öncedir. "
                            "Bu dönemde portföy değeri 0 veya sabit nakit olarak "
                            "görüneceğinden kıyaslama yanıltıcı olabilir."
                        )
                except Exception as exc:
                    logger.debug("Failed to get first trade date for %s: %s", code, exc)

        if (end_date - start_date).days < 7:
            warnings.append(
                "Seçilen tarih aralığı çok kısa (7 günden az). "
                "Yıllıklandırılmış volatilite ve drawdown hesaplamaları kararsız olabilir."
            )
        return warnings

    # ------------------------------------------------------------------
    # Ana veri isteği
    # ------------------------------------------------------------------

    def request_refresh(self) -> None:
        """Ribbon filtrelere göre tüm grafikleri yeniler."""
        page = self.page
        start_date, end_date = page.ribbon_bar.date_range()
        selected_codes = page.ribbon_bar.selected_assets()

        if not selected_codes:
            page._renderer.render_empty_state("Lütfen kıyaslanacak varlıkları seçin.")
            return

        has_holdings_trigger = False
        new_selected_codes = list(selected_codes)
        for code in selected_codes:
            if code.startswith("holdings:"):
                has_holdings_trigger = True
                portfolio_code = code.split(":", 1)[1]
                try:
                    stock_map = self.analysis_service.get_stock_map_for_source(portfolio_code)
                    if stock_map:
                        if portfolio_code not in new_selected_codes:
                            new_selected_codes.append(portfolio_code)
                        for sid, ticker in stock_map.items():
                            sid_str = str(sid)
                            page._asset_labels[sid_str] = ticker
                            if sid_str not in new_selected_codes:
                                new_selected_codes.append(sid_str)
                except Exception as exc:
                    logger.error("Error loading holdings in refresh: %s", exc)

        if has_holdings_trigger:
            updated_assets = self.get_current_base_assets()
            page.ribbon_bar.blockSignals(True)
            try:
                page.ribbon_bar.set_assets(updated_assets)
                page.ribbon_bar.set_selected_assets(new_selected_codes)
            finally:
                page.ribbon_bar.blockSignals(False)
            selected_codes = new_selected_codes

        page.chart_overrides.clear()
        self.refresh_panel_options()

        warnings = self.check_date_warnings()
        if warnings:
            warning_text = "<b>⚠️ Dikkat:</b><br>" + "<br>".join([f"• {w}" for w in warnings])
            page.warning_label.setText(warning_text)
            page.warning_panel.setVisible(True)
        else:
            page.warning_panel.setVisible(False)

        page._request_seq += 1
        request_id = page._request_seq

        portfolio_sources: list[str] = []
        benchmarks: list[str] = []
        stock_ids: list[int] = []

        for code in selected_codes:
            if code == "dashboard" or code.startswith("portfolio:") or code.startswith("model:"):
                portfolio_sources.append(code)
            elif code in {"bist100", "gold", "silver", "usd", "euro", "deposit", "cpi"}:
                benchmarks.append(code)
            else:
                try:
                    stock_ids.append(int(code))
                except ValueError:
                    pass

        page._selected_stock_ids = stock_ids
        primary_source = portfolio_sources[0] if portfolio_sources else "dashboard"

        filter_state = AnalysisFilterState(
            start_date=start_date,
            end_date=end_date,
            selected_stock_ids=stock_ids,
            selected_benchmarks=benchmarks,
            portfolio_source=primary_source,
            comparison_portfolio_sources=portfolio_sources,
            currency_mode="TL",
        )
        worker = Worker(self.analysis_service.get_comparison_view, filter_state)
        worker.signals.result.connect(
            lambda result, rid=request_id: self._on_data_ready(rid, result)
        )
        worker.signals.error.connect(
            lambda err, rid=request_id: self._on_data_error(rid, err)
        )
        self.threadpool.start(worker)

    def _on_data_ready(self, request_id: int, dto) -> None:
        """Worker sonucu döndüğünde grafikleri render eder."""
        page = self.page
        if request_id != page._request_seq:
            return

        series_dict: dict[str, pd.Series] = {}
        page.code_to_label = {}

        if dto.portfolio_series:
            p_series = pd.Series(
                {pd.Timestamp(d): float(v) for d, v in dto.portfolio_series.items()}
            )
            p_series.name = dto.current_portfolio_label
            series_dict[dto.current_portfolio_label] = p_series
            page.code_to_label["dashboard"] = dto.current_portfolio_label

        for cp in dto.comparison_portfolios:
            if cp.points:
                s = pd.Series({pd.Timestamp(d): float(v) for d, v in cp.points.items()})
                s.name = cp.label
                series_dict[cp.label] = s
                page.code_to_label[cp.code] = cp.label
                page.code_to_label[f"portfolio:{cp.code}"] = cp.label

        for b in dto.benchmark_series:
            if b.points:
                s = pd.Series({pd.Timestamp(d): float(v) for d, v in b.points.items()})
                s.name = b.label
                series_dict[b.label] = s
                page.code_to_label[b.code] = b.label

        selected_sids = getattr(page, "_selected_stock_ids", [])
        if selected_sids:
            for stock_id, points in dto.stock_series.items():
                if points:
                    s = pd.Series({pd.Timestamp(d): float(v) for d, v in points.items()})
                    s.name = str(stock_id)
                    series_dict[s.name] = s
                    page.code_to_label[str(stock_id)] = s.name

        if not series_dict:
            page._renderer.render_empty_state("Seçilen filtreler için veri bulunamadı.")
            return

        aligned_df = ComparisonService.align_financial_series(series_dict)
        page.last_global_df = aligned_df
        page._renderer.render_charts(aligned_df)
        page._last_loaded_assets = page.ribbon_bar.selected_assets()
        page._last_loaded_dates = page.ribbon_bar.date_range()

    def _on_data_error(self, request_id: int, err_tuple) -> None:
        """Worker hata döndürdüğünde boş durum gösterir."""
        page = self.page
        if request_id != page._request_seq:
            return
        page._renderer.render_empty_state(f"Veri yükleme hatası: {err_tuple[1]}")

    # ------------------------------------------------------------------
    # Yardımcı
    # ------------------------------------------------------------------

    def find_column_by_code(self, df: pd.DataFrame, code: str) -> str | None:
        """Kod'a karşılık gelen DataFrame sütun adını bulur."""
        page = self.page
        if not hasattr(page, "code_to_label"):
            page.code_to_label = {}

        label = page.code_to_label.get(code)
        if label and label in df.columns:
            return label

        for col in df.columns:
            if col.lower() == code.lower():
                return col
            if code.isdigit() and col == code:
                return col
            if code.lower().replace(" ", "").replace("_", "") in col.lower().replace(" ", "").replace("_", ""):
                return col

        return df.columns[0] if not df.empty else None

    # ------------------------------------------------------------------
    # page_enter hook
    # ------------------------------------------------------------------

    def on_page_enter(self) -> None:
        """Sayfaya girildiğinde varlık listesi değiştiyse yeniler."""
        page = self.page
        old_assets = getattr(page, "_base_assets_cache", [])
        self.load_initial_options()
        new_assets = getattr(page, "_base_assets_cache", [])

        current_assets = page.ribbon_bar.selected_assets()
        current_dates = page.ribbon_bar.date_range()

        if (
            old_assets != new_assets
            or not hasattr(page, "_last_loaded_assets")
            or page._last_loaded_assets != current_assets
            or page._last_loaded_dates != current_dates
        ):
            self.request_refresh()
