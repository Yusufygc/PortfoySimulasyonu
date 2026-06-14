# Code Quality Baseline - 2026-06-13

> Ana sayfa: [index.md](index.md) | Guardrail: [code_quality_guardrails.md](code_quality_guardrails.md)

Bu rapor `scripts/measure_code_quality.py` ile uretilen tekrarlanabilir baseline'dir.
`PortfoySimulasyonu_saglik_raporu.html` referans girdi olarak kullanilir; refactor karari bu metriklerle dogrulanir.

## Ozet

- Git commit: `7b85321`
- Dosya: 440
- Sinif: 538
- Fonksiyon/metot: 3405
- Effective code lines: 44383
- Ihlalli sinif: 1
- Ihlalli fonksiyon/metot: 83
- Saglik raporu eslesen dosya: 84/84

## Katman Ozeti

| Katman | Dosya | Effective satir | Dosya ihlali |
|---|---:|---:|---:|
| src | 330 | 31506 | 1 |
| tests | 95 | 11246 | 0 |
| scripts | 14 | 1603 | 0 |
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
| src/ui/widgets/dashboard/dialogs/new_stock_trade_dialog.py | src | 434 | 1 | 20 | 6 | ok |
| src/ui/pages/stock_detail/stock_detail_page.py | src | 417 | 1 | 17 | 8 | violation |
| src/ui/pages/comparison/utils/chart_renderer.py | src | 416 | 1 | 19 | 5 | ok |
| src/application/services/planning/risk_profile_service.py | src | 394 | 4 | 15 | 3 | ok |
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
| scripts/replicate_db.py | main | 64 | 0 | 13 | function_effective_lines, function_complexity |
| tests/ui/pages/ai_page/test_ai_page_right_panel.py | test_panel_integration | 62 | 1 | 1 | function_effective_lines |
| tests/ui/pages/test_table_selection_behavior.py | test_model_positions_table_is_passive_and_preserves_colored_profit_loss | 61 | 0 | 4 | function_effective_lines |
| tests/ui/pages/test_model_portfolio_page.py | test_model_portfolio_export_today_blocks_when_history_prices_are_missing | 55 | 1 | 2 | function_effective_lines |
| tests/ui/pages/test_model_portfolio_page.py | test_model_portfolio_update_view_passes_previous_close_map | 55 | 1 | 3 | function_effective_lines |
| tests/infrastructure/market_data/test_benchmark_fetch_manual.py | main | 52 | 0 | 18 | function_effective_lines, function_complexity |
| src/infrastructure/corporate_actions/kap_mkk_provider.py | parse_kap_mkk_disclosure | 50 | 1 | 15 | function_complexity |
| src/application/services/planning/model_portfolio_trade_service.py | add_trade | 48 | 7 | 1 | function_effective_params |
| src/ui/pages/comparison/utils/chart_renderer.py | _generate_html_in_background | 48 | 6 | 12 | function_effective_params, function_complexity |
| scripts/migrate_ui_strings.py | is_user_facing_string | 47 | 2 | 35 | function_complexity |
| src/application/services/analysis/portfolio_series_builder.py | _run_simulation_loop | 47 | 12 | 10 | function_effective_params |
| src/application/services/portfolio/trade_entry_service.py | submit_trade | 47 | 8 | 7 | function_effective_params |
| src/infrastructure/market_data/investing_fallback_client.py | fetch_series_for_ticker | 46 | 3 | 11 | function_complexity |
| src/ui/pages/ai_page/left_panel/performance_card.py | update_data | 46 | 8 | 9 | function_effective_params |
| src/ui/pages/ai_page/left_panel/xai_card.py | update_data | 46 | 7 | 12 | function_effective_params, function_complexity |
| src/application/services/planning/model_portfolio_trade_service.py | add_trade_by_ticker | 45 | 8 | 11 | function_effective_params, function_complexity |
| src/ui/pages/dashboard/dashboard_presenter.py | refresh_data | 45 | 0 | 11 | function_complexity |
| src/ui/widgets/shared/feedback/toast.py | _reposition_for_parent | 45 | 2 | 11 | function_complexity |
| scripts/migrate_ui_strings.py | process_file | 44 | 2 | 14 | function_complexity |
| src/ui/pages/model_portfolio/utils/model_portfolio_actions.py | on_trade | 44 | 1 | 12 | function_complexity |
| src/ui/widgets/planning/panels/budget_form_panel.py | _build_item_column | 44 | 8 | 1 | function_effective_params |
| src/application/services/planning/model_portfolio_trade_service.py | add_capital_movement | 43 | 6 | 5 | function_effective_params |
| src/ui/pages/analysis/analysis_overview_section.py | set_data | 43 | 1 | 12 | function_complexity |
| src/application/services/analysis/portfolio_series_builder.py | compute_portfolio_series | 41 | 8 | 5 | function_effective_params |
| src/ui/pages/stock_detail/stock_trade_submitter.py | _submit_model_trade | 41 | 5 | 11 | function_complexity |
| src/domain/models/corporate_action_candidate.py | discovered | 40 | 13 | 1 | function_effective_params |
| src/application/services/analysis/analysis_service.py | __init__ | 38 | 7 | 1 | function_effective_params |
| src/application/services/simulation/history_snapshot_builder.py | build | 37 | 7 | 4 | function_effective_params |

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
