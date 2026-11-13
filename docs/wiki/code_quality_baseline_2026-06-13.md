# Code Quality Baseline - 2026-06-13

> Ana sayfa: [index.md](index.md) | Guardrail: [code_quality_guardrails.md](code_quality_guardrails.md)

Bu rapor `scripts/measure_code_quality.py` ile uretilen tekrarlanabilir baseline'dir.
`PortfoySimulasyonu_saglik_raporu.html` referans girdi olarak kullanilir; refactor karari bu metriklerle dogrulanir.

## Ozet

- Git commit: `a2d1601`
- Dosya: 440
- Sinif: 572
- Fonksiyon/metot: 3457
- Effective code lines: 44375
- Ihlalli sinif: 1
- Ihlalli fonksiyon/metot: 19
- Saglik raporu eslesen dosya: 84/84

## Katman Ozeti

| Katman | Dosya | Effective satir | Dosya ihlali |
|---|---:|---:|---:|
| src | 330 | 31492 | 1 |
| tests | 95 | 11252 | 0 |
| scripts | 14 | 1603 | 0 |
| root | 1 | 28 | 0 |

## En Buyuk Dosyalar

| Dosya | Katman | Effective satir | Sinif | Metot | Fonksiyon | Durum |
|---|---|---:|---:|---:|---:|---|
| src/ui/shared/locale_tr.py | src | 797 | 1 | 0 | 0 | ok |
| src/application/services/market/price_data_health_service.py | src | 701 | 13 | 42 | 11 | ok |
| tests/ui/pages/test_model_portfolio_page.py | tests | 659 | 17 | 43 | 24 | ok |
| scripts/measure_code_quality.py | scripts | 589 | 3 | 10 | 40 | ok |
| src/application/services/planning/model_portfolio_trade_service.py | src | 512 | 8 | 30 | 9 | ok |
| tests/application/test_analysis_service.py | tests | 510 | 12 | 23 | 20 | ok |
| tests/application/test_price_data_health_service.py | tests | 468 | 6 | 18 | 22 | ok |
| tests/ui/pages/test_stock_detail_page.py | tests | 453 | 5 | 10 | 33 | ok |
| tests/ui/pages/test_comparison_page.py | tests | 443 | 10 | 22 | 26 | ok |
| src/ui/widgets/dashboard/dialogs/new_stock_trade_dialog.py | src | 434 | 1 | 20 | 6 | ok |
| src/ui/pages/stock_detail/stock_detail_page.py | src | 417 | 1 | 17 | 8 | violation |
| src/ui/pages/comparison/utils/chart_renderer.py | src | 413 | 3 | 20 | 7 | ok |
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
| scripts/migrate_ui_strings.py | is_user_facing_string | 47 | 2 | 35 | function_complexity |
| scripts/migrate_ui_strings.py | process_file | 44 | 2 | 14 | function_complexity |
| tests/ui/test_refactor_guards.py | test_ui_user_facing_text_uses_l10n_not_hardcoded_literals | 34 | 0 | 13 | function_complexity |
| tests/application/test_price_data_health_service.py | make_service | 33 | 6 | 6 | function_effective_params |
| tests/ui/test_app_startup.py | test_main_window_initial_size_matches_analysis_layout_contract | 30 | 0 | 14 | function_complexity |
| tests/application/test_excel_report_builder.py | _pos | 25 | 7 | 2 | function_effective_params |
| tests/application/test_corporate_action_service.py | _make_action | 19 | 6 | 2 | function_effective_params |
| tests/application/test_excel_report_builder.py | _snap | 19 | 7 | 1 | function_effective_params |
| tests/conftest.py | _build | 18 | 7 | 2 | function_effective_params |
| tests/conftest.py | _build | 16 | 6 | 2 | function_effective_params |
| tests/ui/test_refactor_guards.py | test_ui_has_no_custom_qthread_classes_or_imports | 15 | 0 | 13 | function_complexity |

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
