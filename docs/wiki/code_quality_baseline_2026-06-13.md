# Code Quality Baseline - 2026-06-13

> Ana sayfa: [index.md](index.md) | Guardrail: [code_quality_guardrails.md](code_quality_guardrails.md)

Bu rapor `scripts/measure_code_quality.py` ile uretilen tekrarlanabilir baseline'dir.
`PortfoySimulasyonu_saglik_raporu.html` referans girdi olarak kullanilir; refactor karari bu metriklerle dogrulanir.

## Ozet

- Git commit: `5d1583b`
- Dosya: 439
- Sinif: 538
- Fonksiyon/metot: 3338
- Effective code lines: 44320
- Ihlalli sinif: 1
- Ihlalli fonksiyon/metot: 122
- Saglik raporu eslesen dosya: 84/84

## Katman Ozeti

| Katman | Dosya | Effective satir | Dosya ihlali |
|---|---:|---:|---:|
| src | 330 | 31468 | 1 |
| tests | 95 | 11246 | 0 |
| scripts | 13 | 1578 | 0 |
| root | 1 | 28 | 0 |

## En Buyuk Dosyalar

| Dosya | Katman | Effective satir | Sinif | Metot | Fonksiyon | Durum |
|---|---|---:|---:|---:|---:|---|
| src/ui/shared/locale_tr.py | src | 797 | 1 | 0 | 0 | ok |
| src/application/services/market/price_data_health_service.py | src | 695 | 10 | 42 | 11 | ok |
| tests/ui/pages/test_model_portfolio_page.py | tests | 659 | 17 | 43 | 24 | ok |
| scripts/measure_code_quality.py | scripts | 589 | 3 | 10 | 40 | ok |
| tests/application/test_price_data_health_service.py | tests | 518 | 6 | 18 | 22 | ok |
| src/application/services/planning/model_portfolio_trade_service.py | src | 514 | 3 | 30 | 6 | ok |
| tests/application/test_analysis_service.py | tests | 504 | 12 | 23 | 19 | ok |
| tests/ui/pages/test_stock_detail_page.py | tests | 455 | 5 | 10 | 33 | ok |
| tests/ui/pages/test_comparison_page.py | tests | 443 | 10 | 22 | 26 | ok |
| src/ui/widgets/dashboard/dialogs/new_stock_trade_dialog.py | src | 432 | 1 | 20 | 5 | ok |
| src/ui/pages/stock_detail/stock_detail_page.py | src | 417 | 1 | 17 | 8 | violation |
| src/ui/pages/comparison/utils/chart_renderer.py | src | 416 | 1 | 19 | 5 | ok |
| src/application/services/planning/risk_profile_service.py | src | 397 | 4 | 15 | 1 | ok |
| src/ui/pages/watchlist_page.py | src | 384 | 1 | 20 | 6 | ok |
| scripts/migrate_ui_strings.py | scripts | 372 | 0 | 0 | 10 | ok |

## Sinif Ihlalleri

| Dosya | Sinif | Effective satir | Metot | Ihlal |
|---|---|---:|---:|---|
| src/ui/shared/locale_tr.py | L10N | 797 | 0 | class_effective_lines |

## Fonksiyon/Metot Ihlalleri

| Dosya | Fonksiyon | Effective satir | Parametre | Complexity | Ihlal |
|---|---|---:|---:|---:|---|
| scripts/migrate_ui_strings.py | main | 116 | 0 | 37 | function_effective_lines, function_complexity |
| scripts/apply_trade_adjustments_schema.py | main | 70 | 0 | 6 | function_effective_lines |
| src/application/container_parts/services.py | _build_feature_services | 66 | 3 | 1 | function_effective_lines |
| scripts/replicate_db.py | main | 64 | 0 | 13 | function_effective_lines, function_complexity |
| tests/ui/pages/ai_page/test_ai_page_right_panel.py | test_panel_integration | 62 | 1 | 1 | function_effective_lines |
| tests/ui/pages/test_table_selection_behavior.py | test_model_positions_table_is_passive_and_preserves_colored_profit_loss | 61 | 0 | 4 | function_effective_lines |
| src/ui/pages/dashboard/dashboard_corporate_action_actions.py | on_corporate_action | 60 | 2 | 10 | function_effective_lines |
| src/ui/pages/model_portfolio/utils/model_portfolio_ui_builder.py | build_ui | 60 | 0 | 1 | function_effective_lines |
| src/application/services/corporate_actions/corporate_action_service.py | _apply_bedelli | 58 | 4 | 7 | function_effective_lines |
| src/ui/pages/comparison/utils/ai_helper.py | generate_commentary | 58 | 0 | 8 | function_effective_lines |
| src/ui/pages/comparison/utils/ai_helper.py | build_panel | 57 | 0 | 1 | function_effective_lines |
| src/application/services/corporate_actions/corporate_action_service.py | _apply_bedelsiz | 55 | 4 | 6 | function_effective_lines |
| src/application/services/corporate_actions/price_adjustment_service.py | adjust_prices_for_applied_action | 55 | 1 | 20 | function_effective_lines, function_complexity |
| tests/ui/pages/test_model_portfolio_page.py | test_model_portfolio_export_today_blocks_when_history_prices_are_missing | 55 | 1 | 2 | function_effective_lines |
| tests/ui/pages/test_model_portfolio_page.py | test_model_portfolio_update_view_passes_previous_close_map | 55 | 1 | 3 | function_effective_lines |
| src/ui/pages/ai_page/left_panel/xai_card.py | _make_factor_row | 54 | 2 | 8 | function_effective_lines |
| src/ui/pages/analysis/analysis_comparison_section.py | __init__ | 53 | 1 | 1 | function_effective_lines |
| src/ui/pages/stock_detail/stock_chart_widget.py | _render_chart | 53 | 4 | 8 | function_effective_lines |
| src/application/services/analysis/portfolio_series_builder.py | _run_simulation_loop | 52 | 12 | 12 | function_effective_lines, function_effective_params, function_complexity |
| src/ui/pages/ai_page/left_panel/performance_card.py | _init_ui | 52 | 0 | 3 | function_effective_lines |
| src/ui/pages/ai_page/right_panel/chatbot_panel.py | _build_prompt_template | 52 | 4 | 27 | function_effective_lines, function_complexity |
| src/ui/pages/dashboard/dashboard_corporate_action_actions.py | _refresh_prices_after_corporate_action | 52 | 3 | 4 | function_effective_lines |
| src/ui/pages/risk_profile_page.py | _build_survey | 52 | 0 | 2 | function_effective_lines |
| tests/infrastructure/market_data/test_benchmark_fetch_manual.py | main | 52 | 0 | 18 | function_effective_lines, function_complexity |
| src/ui/pages/comparison/utils/comparison_data_manager.py | request_refresh | 51 | 0 | 10 | function_effective_lines |
| src/infrastructure/corporate_actions/kap_mkk_provider.py | parse_kap_mkk_disclosure | 50 | 1 | 15 | function_complexity |
| src/ui/pages/settings/utils/price_data_report.py | format_report_text | 50 | 1 | 13 | function_complexity |
| src/infrastructure/ai/ai_core_fastapi_client.py | _parse_peer | 49 | 1 | 14 | function_complexity |
| src/ui/pages/settings/utils/price_data_report.py | on_health_selection_changed | 49 | 0 | 15 | function_complexity |
| src/application/services/analysis/analysis_service.py | get_overview | 48 | 2 | 17 | function_complexity |

## Saglik Raporu Crosswalk

Saglik HTML'i tek kaynak degildir. Bu bolum yalniz HTML'de adi gecen dosyalarin yeni metriklerle eslesip eslesmedigini gosterir.

| Metrik | Deger |
|---|---:|
| HTML'de bulunan repo dosyasi | 84 |
| Olcumde eslesen dosya | 84 |

## Refactor Onceligi

1. Application servis facade'lari: fiyat sagligi, model portfoy trade, kurumsal aksiyon, risk profili ve optimizasyon.
2. UI page/widget ayrimi: buyuk `_init_ui`, tablo doldurma, chart cizimi ve worker orchestration bloklari.
3. Infrastructure ve dependency temizligi: yalniz dogrulanmis kullanilmayan paketler kaldirilir.
