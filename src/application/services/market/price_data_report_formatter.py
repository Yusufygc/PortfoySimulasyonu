"""Fiyat verisi sağlık raporunu UI'dan bağımsız HTML / düz metin olarak biçimlendirir."""
from __future__ import annotations

from src.application.services.market.price_data_health_service import (
    PriceDataHealthReport,
    StockPriceHealthRow,
)

_DATE_FMT = "%d.%m.%Y"
_MAX_LISTED_DAYS = 80
_MAX_LISTED_HOLIDAYS = 40
_MAX_LISTED_STOCKS = 20


def display_ticker(ticker: str) -> str:
    return (ticker or "").replace(".IS", "").strip().upper()


def is_healthy(status: str) -> bool:
    return "Sağlıklı" in (status or "")


def _dates_text(dates, limit: int) -> str:
    text = ", ".join(d.strftime(_DATE_FMT) for d in dates[:limit])
    if len(dates) > limit:
        text += f"<br>... +{len(dates) - limit} gün"
    return text


def format_stock_detail_html(row: StockPriceHealthRow, report: PriceDataHealthReport) -> str:
    missing = _dates_text(row.missing_dates, _MAX_LISTED_DAYS) or "<span style='color:#94a3b8;'>Eksik gün yok.</span>"
    known = _dates_text(report.known_holiday_dates, 60) or "<span style='color:#94a3b8;'>Bu aralıkta kayıtlı tatil yok.</span>"
    candidates = _dates_text(report.holiday_candidate_dates, 60) or "<span style='color:#94a3b8;'>Tatil adayı yok.</span>"
    status_color = "#10b981" if is_healthy(row.status) else "#ef4444"
    last_date = row.last_price_date.strftime(_DATE_FMT) if row.last_price_date else "-"
    return (
        f"<h3 style='color:#3b82f6;'>{display_ticker(row.ticker)}</h3>"
        f"<p><b>Durum:</b> <span style='color:{status_color};'>{row.status}</span><br>"
        f"<b>Son Veri:</b> {last_date}</p>"
        f"<p><b style='color:#ef4444;'>Eksik Günler ({row.missing_count}):</b><br>{missing}</p>"
        f"<p><b style='color:#3b82f6;'>Bilinen BIST Tatilleri ({report.known_holiday_count}):</b><br>{known}</p>"
        f"<p><b style='color:#ca8a04;'>Tatil Adayları ({report.holiday_candidate_count}):</b><br>{candidates}</p>"
    )


def format_report_html(report: PriceDataHealthReport) -> str:
    problematic = [row for row in report.rows if row.missing_count > 0]
    status_color = "#10b981" if is_healthy(report.health_label) else "#ef4444"
    if problematic:
        items = "".join(
            f"<li>{display_ticker(r.ticker)}: <span style='color:#ef4444;'>{r.missing_count} eksik</span></li>"
            for r in problematic[:_MAX_LISTED_STOCKS]
        )
        if len(problematic) > _MAX_LISTED_STOCKS:
            items += f"<li>... ve {len(problematic) - _MAX_LISTED_STOCKS} hisse daha</li>"
    else:
        items = "<li>Yok</li>"
    known = _dates_text(report.known_holiday_dates, _MAX_LISTED_HOLIDAYS) or "Yok"
    candidates = _dates_text(report.holiday_candidate_dates, _MAX_LISTED_HOLIDAYS) or "Yok"
    return (
        "<h3 style='color:#3b82f6;'>Fiyat Verisi Sağlık Raporu</h3>"
        f"<p><b>Aralık:</b> {report.start_date:{_DATE_FMT}} - {report.end_date:{_DATE_FMT}}<br>"
        f"<b>Durum:</b> <span style='color:{status_color};'><b>{report.health_label}</b></span></p>"
        f"<p><b>Hisse:</b> {report.total_stock_count}<br>"
        f"<b>Beklenen İşlem Günü:</b> {report.expected_business_day_count}<br>"
        f"<b>Eksik Kayıt:</b> <span style='color:#ef4444;'>{report.total_missing_count}</span><br>"
        f"<b>Bilinen Tatil:</b> <span style='color:#3b82f6;'>{report.known_holiday_count}</span><br>"
        f"<b>Tatil Adayı (heuristik):</b> <span style='color:#ca8a04;'>{report.holiday_candidate_count}</span></p>"
        f"<p><b style='color:#ef4444;'>Sorunlu Hisseler:</b></p><ul>{items}</ul>"
        f"<p><b style='color:#3b82f6;'>Bilinen BIST Tatilleri ({report.known_holiday_count}):</b><br>{known}</p>"
        f"<p><b style='color:#ca8a04;'>Tatil Adayları - heuristik ({report.holiday_candidate_count}):</b><br>{candidates}</p>"
    )


def format_report_text(report: PriceDataHealthReport) -> str:
    """Panoya kopyalanacak düz metin raporu."""
    lines = [
        "Fiyat Verisi Sağlık Raporu",
        f"Aralık: {report.start_date:{_DATE_FMT}} - {report.end_date:{_DATE_FMT}}",
        f"Durum: {report.health_label}",
        f"Hisse: {report.total_stock_count}",
        f"Beklenen İşlem Günü: {report.expected_business_day_count}",
        f"Eksik Kayıt: {report.total_missing_count}",
        f"Bilinen Tatil: {report.known_holiday_count}",
        f"Tatil Adayı (heuristik): {report.holiday_candidate_count}",
        "",
        "Sorunlu Hisseler:",
    ]
    problematic = [row for row in report.rows if row.missing_count > 0]
    if not problematic:
        lines.append("  Yok")
    for row in problematic:
        first = row.first_missing_date.strftime(_DATE_FMT) if row.first_missing_date else "-"
        last = row.last_missing_date.strftime(_DATE_FMT) if row.last_missing_date else "-"
        lines.append(f"  {display_ticker(row.ticker)}: {row.missing_count} eksik ({first} - {last})")
    return "\n".join(lines)
