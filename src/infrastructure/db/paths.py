"""Veri dosyası yolları — tek kaynak.

Uygulamanın iki yerel veritabanı vardır:
- SQLite  (`portfolio.db`)          : işlemsel (OLTP) veri — portföy, işlemler, listeler, planlama, ayarlar...
- DuckDB  (`market_history.duckdb`) : analitik piyasa geçmişi (OLAP) — tüm BIST günlük barları

Yollar çalışma dizinine (cwd) değil uygulama köküne göre çözülür; böylece uygulama farklı bir
dizinden veya Nuitka ile derlenmiş .exe olarak başlatıldığında da aynı dosyaları bulur.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

DEFAULT_SQLITE_RELATIVE = "data/portfolio.db"
DUCKDB_FILE_NAME = "market_history.duckdb"


def app_root() -> Path:
    """Geliştirmede proje kökü, derlenmiş uygulamada .exe'nin bulunduğu dizin."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[3]


def resolve_data_path(path: str | os.PathLike) -> Path:
    """Göreli yolu uygulama köküne göre mutlak yola çevirir; mutlak yolu olduğu gibi bırakır."""
    candidate = Path(path)
    return candidate if candidate.is_absolute() else (app_root() / candidate)


def sqlite_db_path(configured: str | os.PathLike | None = None) -> Path:
    return resolve_data_path(configured or DEFAULT_SQLITE_RELATIVE)


def duckdb_path(sqlite_path: str | os.PathLike | None = None) -> Path:
    """DuckDB dosyası; `DUCKDB_PATH` ortam değişkeniyle değiştirilebilir, yoksa SQLite dosyasının yanındadır."""
    override = os.getenv("DUCKDB_PATH")
    if override:
        return resolve_data_path(override)
    return sqlite_db_path(sqlite_path).parent / DUCKDB_FILE_NAME
