# Code Quality Baseline - 2026-06-13

> Ana sayfa: [index.md](index.md) | Guardrail: [code_quality_guardrails.md](code_quality_guardrails.md)

Bu rapor `scripts/measure_code_quality.py` ile uretilen tekrarlanabilir baseline'dir.
`PortfoySimulasyonu_saglik_raporu.html` referans girdi olarak kullanilir; refactor karari bu metriklerle dogrulanir.

## Ozet

- Git commit: `527b878`
- Dosya: 438
- Sinif: 536
- Fonksiyon/metot: 3251
- Effective code lines: 44105
- Ihlalli sinif: 12
- Ihlalli fonksiyon/metot: 155
- Saglik raporu eslesen dosya: 84/84

## Katman Ozeti

| Katman | Dosya | Effective satir | Dosya ihlali |
|---|---:|---:|---:|
| src | 329 | 31246 | 0 |
| tests | 95 | 11253 | 0 |
| scripts | 13 | 1578 | 0 |
| root | 1 | 28 | 0 |

## En Buyuk Dosyalar

| Dosya | Katman | Effective satir | Sinif | Metot | Fonksiyon | Durum |
|---|---|---:|---:|---:|---:|---|
| src/ui/shared/locale_tr.py | src | 797 | 1 | 0 | 0 | ok |
| src/application/services/market/price_data_health_service.py | src | 695 | 10 | 42 | 11 | ok |
| tests/ui/pages/test_model_portfolio_page.py | tests | 659 | 17 | 43 | 24 | ok |
| scripts/measure_code_quality.py | scripts | 589 | 3 | 10 | 40 | ok |
| src/application/services/planning/model_portfolio_trade_service.py | src | 528 | 3 | 36 | 0 | ok |
| tests/application/test_price_data_health_service.py | tests | 518 | 6 | 18 | 22 | ok |
| tests/application/test_analysis_service.py | tests | 504 | 12 | 23 | 19 | ok |
| tests/ui/pages/test_stock_detail_page.py | tests | 455 | 5 | 10 | 33 | ok |
| tests/ui/pages/test_comparison_page.py | tests | 443 | 10 | 22 | 26 | ok |
| src/ui/pages/comparison/utils/chart_renderer.py | src | 420 | 1 | 22 | 1 | ok |
| src/ui/widgets/dashboard/dialogs/new_stock_trade_dialog.py | src | 415 | 1 | 23 | 0 | ok |
| src/ui/pages/stock_detail/stock_detail_page.py | src | 399 | 1 | 16 | 3 | ok |
| src/application/services/planning/risk_profile_service.py | src | 397 | 4 | 15 | 1 | ok |
| src/ui/pages/ai_page/right_panel/chatbot_panel.py | src | 392 | 1 | 31 | 0 | ok |
| src/ui/pages/watchlist_page.py | src | 380 | 1 | 20 | 2 | ok |

## Sinif Ihlalleri

| Dosya | Sinif | Effective satir | Metot | Ihlal |
|---|---|---:|---:|---|
| src/ui/shared/locale_tr.py | L10N | 797 | 0 | class_effective_lines |
| src/ui/widgets/dashboard/dialogs/new_stock_trade_dialog.py | NewStockTradeDialog | 396 | 23 | class_effective_lines, class_methods |
| src/application/services/planning/model_portfolio_trade_service.py | ModelPortfolioTradeService | 382 | 26 | class_effective_lines, class_methods |
| src/ui/pages/ai_page/right_panel/chatbot_panel.py | ChatbotPanel | 374 | 31 | class_effective_lines, class_methods |
| src/ui/pages/comparison/utils/chart_renderer.py | ChartRenderer | 369 | 22 | class_effective_lines, class_methods |
| src/ui/pages/stock_detail/stock_detail_page.py | StockDetailPage | 369 | 16 | class_effective_lines |
| src/ui/pages/watchlist_page.py | WatchlistPage | 352 | 20 | class_effective_lines |
| src/ui/pages/risk_profile_page.py | RiskProfilePage | 330 | 22 | class_effective_lines, class_methods |
| src/ui/pages/settings/price_data_panel.py | PriceDataPanel | 260 | 22 | class_methods |
| src/ui/widgets/shared/controls/currency_spin_box.py | CurrencySpinBox | 203 | 27 | class_methods |
| src/infrastructure/db/sqlalchemy/repositories/sa_model_portfolio_repository.py | SQLAlchemyModelPortfolioRepository | 168 | 22 | class_methods |
| src/application/services/planning/model_portfolio_service.py | ModelPortfolioService | 72 | 24 | class_methods |

## Fonksiyon/Metot Ihlalleri

| Dosya | Fonksiyon | Effective satir | Parametre | Complexity | Ihlal |
|---|---|---:|---:|---:|---|
| src/ui/pages/stock_detail/stock_detail_page.py | _init_ui | 129 | 0 | 2 | function_effective_lines |
| scripts/migrate_ui_strings.py | main | 116 | 0 | 37 | function_effective_lines, function_complexity |
| src/ui/widgets/dashboard/dialogs/corporate_action_dialog.py | _init_ui | 110 | 0 | 3 | function_effective_lines |
| src/infrastructure/ai/ai_core_fastapi_client.py | _parse_api_response | 109 | 1 | 15 | function_effective_lines, function_complexity |
| src/ui/pages/comparison/widgets/ribbon_bar.py | _init_ui | 105 | 0 | 2 | function_effective_lines |
| src/ui/pages/watchlist_page.py | _init_ui | 102 | 0 | 1 | function_effective_lines |
| src/ui/widgets/stock/dialogs/trade_dialog.py | _init_ui | 96 | 0 | 2 | function_effective_lines |
| src/ui/pages/ai_page/left_panel/peer_card.py | update_data | 91 | 1 | 28 | function_effective_lines, function_complexity |
| src/ui/pages/analysis/chart_builder.py | build_performance_line_chart_v2 | 90 | 4 | 6 | function_effective_lines |
| src/application/services/planning/optimization_service.py | _optimize | 89 | 2 | 19 | function_effective_lines, function_complexity |
| src/ui/pages/settings/reset_panel.py | _init_ui | 87 | 0 | 2 | function_effective_lines |
| src/ui/widgets/planning/panels/goals_panel.py | load | 87 | 1 | 9 | function_effective_lines |
| src/application/container_parts/services.py | _build_feature_services | 85 | 3 | 1 | function_effective_lines |
| src/ui/pages/analysis/analysis_comparison_section.py | _redraw_chart | 81 | 0 | 23 | function_effective_lines, function_complexity |
| src/ui/widgets/dashboard/dialogs/new_stock_trade_dialog.py | _init_page2 | 78 | 0 | 1 | function_effective_lines |
| src/application/services/analysis/portfolio_series_builder.py | _run_simulation_loop | 77 | 12 | 28 | function_effective_lines, function_effective_params, function_complexity |
| src/ui/widgets/model_portfolio/dialogs/trade_input_dialog.py | _init_ui | 77 | 0 | 2 | function_effective_lines |
| src/ui/pages/analysis/analysis_page.py | _init_ui | 76 | 0 | 1 | function_effective_lines |
| src/ui/pages/analysis/analysis_control_panel.py | _init_ui | 75 | 0 | 2 | function_effective_lines |
| src/ui/pages/ai_page/left_panel/xai_card.py | _init_ui | 73 | 0 | 1 | function_effective_lines |
| scripts/apply_trade_adjustments_schema.py | main | 70 | 0 | 6 | function_effective_lines |
| src/ui/pages/ai_page/left_panel/prediction_card.py | _init_ui | 70 | 0 | 1 | function_effective_lines |
| src/ui/pages/dashboard/dashboard_page.py | _init_ui | 70 | 0 | 1 | function_effective_lines |
| src/application/services/analysis/analysis_bundle_builder.py | build | 69 | 1 | 12 | function_effective_lines, function_complexity |
| src/ui/pages/stock_detail/trade_form_panel.py | _init_ui | 69 | 0 | 1 | function_effective_lines |
| src/ui/pages/ai_page/left_panel/prediction_card.py | update_data | 66 | 12 | 15 | function_effective_lines, function_effective_params, function_complexity |
| src/ui/pages/ai_page/right_panel/chatbot_panel.py | _build_prompt_template | 65 | 4 | 27 | function_effective_lines, function_complexity |
| src/ui/pages/optimization_page.py | _init_ui | 65 | 0 | 1 | function_effective_lines |
| src/ui/pages/risk_profile_page.py | _build_profile_card | 65 | 0 | 2 | function_effective_lines |
| scripts/replicate_db.py | main | 64 | 0 | 13 | function_effective_lines, function_complexity |

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
