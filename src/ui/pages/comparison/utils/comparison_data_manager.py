# src/ui/pages/comparison/utils/comparison_data_manager.py
"""Karşılaştırma sayfasının veri ve filtre yönetimi."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pandas as pd
from PyQt5.QtCore import QThreadPool

from src.ui.worker import Worker
from src.application.services.analysis.models import AnalysisFilterState
from src.application.services.analysis.comparison_service import ComparisonService
from src.ui.pages.comparison.utils.comparison_asset_options import ComparisonAssetOptions
from src.ui.pages.comparison.utils.comparison_filter_state_builder import ComparisonFilterStateBuilder
from src.ui.pages.comparison.utils.comparison_series_builder import ComparisonSeriesBuilder
from src.ui.pages.comparison.utils.comparison_warning_builder import ComparisonWarningBuilder

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
        self._asset_options = ComparisonAssetOptions(
            page,
            analysis_service,
            self.handle_chart_portfolio_selected,
        )
        self._filter_state_builder = ComparisonFilterStateBuilder(page, analysis_service)
        self._warning_builder = ComparisonWarningBuilder(page, analysis_service)

    # ------------------------------------------------------------------
    # Varlık seçeneklerini yükleme
    # ------------------------------------------------------------------

    def get_current_base_assets(self) -> list[tuple[str, str]]:
        """Tüm portföy, benchmark ve çözümlenmiş hisse seçeneklerini döner."""
        return self._asset_options.get_current_base_assets()

    def load_initial_options(self) -> None:
        """Ribbon bar'ı başlangıç seçenekleriyle doldurur."""
        self._asset_options.load_initial_options()

    def refresh_panel_options(self) -> None:
        """Her grafik panelinin portföy override menüsünü günceller."""
        self._asset_options.refresh_panel_options()

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
                if chart_key == "main_chart" or chart_key == "main":
                    page._renderer.render_single_chart_async("main", page.last_global_df)
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
                    page._renderer.render_single_chart_async(chart_key, df_metrics)
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

        series_dict, label_updates = ComparisonSeriesBuilder.build_override_series(
            dto,
            portfolio_code,
            getattr(page, "_asset_labels", {}),
        )
        page.code_to_label.update(label_updates)

        if not series_dict:
            return

        aligned_df = ComparisonService.align_financial_series(series_dict)
        mode = page.ribbon_bar.selected_mode()

        if chart_key == "main_chart" or chart_key == "main":
            page._renderer.render_single_chart_async("main", aligned_df)
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
            page._renderer.render_single_chart_async(chart_key, df_metrics)

    # ------------------------------------------------------------------
    # Tarih doğrulama
    # ------------------------------------------------------------------

    def check_date_warnings(self) -> list[str]:
        """Seçili tarihlere ilişkin doğrulama uyarıları döner."""
        return self._warning_builder.check_date_warnings()

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

        new_selected_codes, has_holdings_trigger = self._filter_state_builder.expand_holdings(selected_codes)

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

        filter_state, stock_ids = self._filter_state_builder.build(selected_codes, start_date, end_date)
        page._selected_stock_ids = stock_ids
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

        selected_sids = getattr(page, "_selected_stock_ids", [])
        series_dict, page.code_to_label = ComparisonSeriesBuilder.build_global_series(dto, selected_sids)

        if not series_dict:
            page._renderer.render_empty_state("Seçilen filtreler için veri bulunamadı.")
            return

        aligned_df = ComparisonService.align_financial_series(series_dict)
        page.last_global_df = aligned_df
        page._renderer.trigger_visible_charts_render(aligned_df)
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
