from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List


class IDatabaseMaintenance(ABC):
    """Veritabanı dosyaları için istatistik, bütünlük kontrolü ve dışa aktarım (Ayarlar > Veri Sağlığı)."""

    sqlite_path: Path
    duckdb_path: Path

    @abstractmethod
    def collect_stats(self) -> Dict[str, Any]: ...

    @abstractmethod
    def check_integrity(self) -> List[str]:
        """Bulunan sorunların metinleri; sorun yoksa boş liste."""

    @abstractmethod
    def export_backup_data(self) -> Dict[str, Any]: ...

    @abstractmethod
    def export_tables_to_excel(self, target_file: Path) -> None: ...
