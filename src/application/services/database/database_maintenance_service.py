"""Ayarlar > Veri Sağlığı ve Dışa Aktarım için veritabanı bakım işlemleri (`IDatabaseMaintenance` portu üzerinden)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from src.domain.ports.services.i_database_maintenance import IDatabaseMaintenance


class DatabaseMaintenanceService:
    def __init__(self, store: IDatabaseMaintenance) -> None:
        self._store = store

    @property
    def sqlite_path(self) -> Path:
        return self._store.sqlite_path

    @property
    def duckdb_path(self) -> Path:
        return self._store.duckdb_path

    def collect_stats(self) -> Dict[str, Any]:
        return self._store.collect_stats()

    def check_integrity(self) -> List[str]:
        return self._store.check_integrity()

    def export_backup_data(self) -> Dict[str, Any]:
        return self._store.export_backup_data()

    def export_tables_to_excel(self, target_file: Path) -> None:
        self._store.export_tables_to_excel(target_file)
