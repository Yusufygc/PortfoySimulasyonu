"""
run.py — Finansal Lab Orchestrator

Tek komutla: scrape → metrics → viz → JSON + HTML kaydet.

Kullanım:
    python run.py FROTO
    python run.py FROTO --quarters 16
    python run.py FROTO --quarters 8 --currency USD
    python run.py FROTO --no-scrape          # mevcut JSON'ı kullan, sadece viz üret
    python run.py FROTO --periods 12         # grafiklerde gösterilecek dönem sayısı
    python run.py FROTO --open               # HTML'i tarayıcıda otomatik aç
    python run.py FROTO EREGL AKBNK          # birden fazla hisse
    python run.py FROTO --no-market          # yfinance verisi alma
    python run.py FROTO --no-tufe            # EVDS/TÜFE verisi alma
    python run.py FROTO TOASO OTKAR --peer --open  # ayrı peer karşılaştırma dashboard
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import time
import webbrowser
from pathlib import Path

def _fix_stdout() -> None:
    """Windows cp1254 fix — __main__ entry-point'te bir kez çağır."""
    if hasattr(sys.stdout, "buffer") and getattr(sys.stdout, "encoding", "") != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer") and getattr(sys.stderr, "encoding", "") != "utf-8":
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


LAB_DIR = Path(__file__).parent


def _header(text: str) -> None:
    bar = "=" * 60
    print(f"\n{bar}")
    print(f"  {text}")
    print(f"{bar}")


def _step(n: int, total: int, label: str) -> None:
    print(f"\n[{n}/{total}] {label}...")


def _inject_market(m: dict, ticker: str) -> None:
    """yfinance anlık veri + değerleme çarpanlarını m'ye enjekte et."""
    try:
        from valuation_provider import get_market_snapshot, compute_valuation
        snap = get_market_snapshot(ticker)
        m["_market_snap"] = snap
        m["_market_val"]  = compute_valuation(m, snap)
        price = snap.get("price")
        mc    = snap.get("market_cap")
        print(f"    [market] {ticker}: fiyat={price} TRY, piyasa değeri={mc/1e9:.1f}B TRY" if mc else
              f"    [market] {ticker}: veri alınamadı — {snap.get('error')}")
    except Exception as e:
        print(f"    [market] UYARI: yfinance hatası ({e}) — değerleme sekmeleri boş kalacak")


def _inject_tufe(m: dict) -> None:
    """EVDS TÜFE verisi al, m'ye enjekte et."""
    try:
        from datetime import date
        from tufe_provider import get_tufe_index
        periods = m.get("periods", [])
        if not periods:
            return
        # En eski dönemden 13 ay önce ile bugüne
        oldest  = periods[-1].split("/")
        start_y = int(oldest[0]) - 1
        start_d = date(start_y, 1, 1)
        end_d   = date.today()
        tufe    = get_tufe_index(start_d, end_d)
        m["_tufe"] = tufe
        if tufe:
            print(f"    [tufe] {len(tufe)} aylık TÜFE endeksi yüklendi")
        else:
            print("    [tufe] UYARI: TÜFE verisi boş — EVDS_API_KEY kontrol edin")
    except Exception as e:
        print(f"    [tufe] UYARI: TÜFE hatası ({e}) — reel büyüme sekmeleri boş kalacak")


def run_one(
    ticker: str,
    *,
    n_quarters: int = 12,
    currency: str = "TRY",
    no_scrape: bool = False,
    n_periods: int = 8,
    open_browser: bool = False,
    no_market: bool = False,
    no_tufe: bool = False,
) -> tuple[Path, Path]:
    """
    Tek hisse için tam pipeline. (JSON path, HTML path) döndür.
    """
    from isyatirim_scraper import fetch_financial_data
    from metrics import compute_metrics, print_summary
    from viz_prototype import build_dashboard

    ticker   = ticker.upper().strip()
    data_dir = LAB_DIR / "data" / ticker
    data_dir.mkdir(parents=True, exist_ok=True)

    json_path = data_dir / f"{ticker.lower()}_{currency.lower()}_finansal.json"
    html_path = data_dir / f"{ticker.lower()}_dashboard.html"

    total_steps = 3

    # ------------------------------------------------------------------ #
    # Adım 1 — Scraping (veya JSON yükleme)
    # ------------------------------------------------------------------ #
    _step(1, total_steps, f"Veri çekiliyor: {ticker} ({n_quarters} çeyrek, {currency})")

    if no_scrape and json_path.exists():
        print(f"    [skip] Mevcut JSON kullanılıyor: {json_path.name}")
        with open(json_path, encoding="utf-8") as f:
            raw = json.load(f)
    else:
        t0  = time.time()
        raw = fetch_financial_data(ticker, n_quarters=n_quarters, currency=currency)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
        elapsed = time.time() - t0
        print(f"    Kaydedildi: {json_path.name}  ({elapsed:.1f}s)")

    periods_fetched = len(raw.get("periods", []))
    secs = raw.get("sections", {})
    print(f"    Donemler: {periods_fetched}  |  "
          f"bilanço={len(secs.get('bilanco',{}))}  "
          f"gelir={len(secs.get('gelir',{}))}  "
          f"dipnot={len(secs.get('dipnot',{}))}  "
          f"nakit={len(secs.get('nakit_akim',{}))} kalem")

    # ------------------------------------------------------------------ #
    # Adım 2 — Metrikler
    # ------------------------------------------------------------------ #
    _step(2, total_steps, "Metrikler hesaplanıyor")

    m = compute_metrics(raw)

    # Dış veri enjeksiyonu (hata halinde sessiz geç)
    if not no_market:
        _inject_market(m, ticker)
    if not no_tufe:
        _inject_tufe(m)

    print_summary(m)

    # ------------------------------------------------------------------ #
    # Adım 3 — Dashboard HTML
    # ------------------------------------------------------------------ #
    _step(3, total_steps, f"Dashboard oluşturuluyor ({n_periods} dönem görünür)")

    html = build_dashboard(m, n_periods=n_periods)
    html_path.write_text(html, encoding="utf-8")
    print(f"    Kaydedildi: {html_path.name}")

    # ------------------------------------------------------------------ #
    # Özet
    # ------------------------------------------------------------------ #
    print(f"\n  JSON  : {json_path}")
    print(f"  HTML  : {html_path}")

    if open_browser:
        webbrowser.open(html_path.as_uri())
        print(f"  Tarayıcı açılıyor...")

    return json_path, html_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Finansal Lab — Scrape + Metrik + Viz pipeline",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""Örnekler:
  python run.py FROTO
  python run.py FROTO --quarters 16 --currency USD
  python run.py FROTO EREGL --periods 12 --open
  python run.py FROTO --no-scrape --open
""",
    )
    p.add_argument(
        "tickers", nargs="+", metavar="TICKER",
        help="Hisse kodu(ları), ör: FROTO EREGL AKBNK",
    )
    p.add_argument(
        "-q", "--quarters", type=int, default=12, metavar="N",
        help="Kaç çeyrek veri çekilsin (varsayılan: 12)",
    )
    p.add_argument(
        "-c", "--currency", default="TRY", choices=["TRY", "USD"],
        help="Para birimi (varsayılan: TRY)",
    )
    p.add_argument(
        "-p", "--periods", type=int, default=8, metavar="N",
        help="Grafiklerde gösterilecek dönem sayısı (varsayılan: 8)",
    )
    p.add_argument(
        "--no-scrape", action="store_true",
        help="Scraping yapma; mevcut JSON'ı kullan",
    )
    p.add_argument(
        "--open", action="store_true",
        help="HTML dashboard'u tarayıcıda aç",
    )
    p.add_argument(
        "--no-market", action="store_true",
        help="yfinance piyasa verisi alma (Değerleme sekmeleri boş kalır)",
    )
    p.add_argument(
        "--no-tufe", action="store_true",
        help="EVDS/TÜFE verisi alma (Reel Büyüme sekmesi boş kalır)",
    )
    p.add_argument(
        "--peer", action="store_true",
        help="Peer karşılaştırma dashboard üret (tüm ticker'lar tek HTML'de)",
    )
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    tickers = [t.upper() for t in args.tickers]
    _header(f"Finansal Lab  |  {', '.join(tickers)}  |  {args.quarters}Q  |  {args.currency}")

    results: list[tuple[str, Path, Path]] = []
    errors:  list[tuple[str, str]]        = []

    metrics_list: list[dict] = []  # peer dashboard için

    for ticker in tickers:
        if len(tickers) > 1:
            print(f"\n{'─'*60}")
            print(f"  >> {ticker}")
            print(f"{'─'*60}")
        try:
            j, h = run_one(
                ticker,
                n_quarters   = args.quarters,
                currency     = args.currency,
                no_scrape    = args.no_scrape,
                n_periods    = args.periods,
                open_browser = args.open and not args.peer,
                no_market    = args.no_market,
                no_tufe      = args.no_tufe,
            )
            results.append((ticker, j, h))

            # Peer için metrikleri topla
            if args.peer:
                from metrics import compute_metrics
                import json as _j
                with open(j, encoding="utf-8") as f:
                    raw = _j.load(f)
                metrics_list.append(compute_metrics(raw))

        except Exception as exc:
            print(f"\n  HATA [{ticker}]: {exc}")
            errors.append((ticker, str(exc)))

    # Peer dashboard
    if args.peer and len(metrics_list) >= 2:
        _header("PEER KARŞILAŞTIRMA DASHBOARD")
        try:
            from peer_viz import build_peer_dashboard
            peer_html = build_peer_dashboard(metrics_list, n_periods=args.periods)
            peer_path = LAB_DIR / "data" / f"peer_{'_'.join(tickers)}.html"
            peer_path.write_text(peer_html, encoding="utf-8")
            print(f"  Peer dashboard: {peer_path}")
            if args.open:
                webbrowser.open(peer_path.as_uri())
        except Exception as exc:
            print(f"  HATA [peer]: {exc}")
    elif args.peer:
        print("  Peer dashboard için en az 2 hisse gerekli.")

    # Çoklu hisse özet tablosu
    if len(tickers) > 1:
        _header("TAMAMLANDI")
        for ticker, j, h in results:
            print(f"  OK  {ticker:<8}  {h}")
        for ticker, err in errors:
            print(f"  ERR {ticker:<8}  {err}")

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    _fix_stdout()
    main()
