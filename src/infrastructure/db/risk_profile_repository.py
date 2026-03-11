# src/infrastructure/db/risk_profile_repository.py

from __future__ import annotations

from typing import List, Optional

from src.domain.models.risk_profile import RiskProfile
from src.domain.services_interfaces.i_risk_profile_repo import IRiskProfileRepository
from .mysql_connection import MySQLConnectionProvider


class MySQLRiskProfileRepository(IRiskProfileRepository):
    """
    IRiskProfileRepository'nin MySQL implementasyonu.
    'risk_profiles' tablosuna erişir.
    """

    def __init__(self, connection_provider: MySQLConnectionProvider) -> None:
        self._cp = connection_provider

    @staticmethod
    def _row_to_profile(row: dict) -> RiskProfile:
        return RiskProfile(
            id=row["id"],
            age=int(row.get("age", 0) or 0),
            horizon=row.get("horizon", "medium"),
            reaction=row.get("reaction", "hold"),
            risk_score=int(row.get("risk_score", 0) or 0),
            risk_label=row.get("risk_label", "DENGELİ"),
            created_at=row.get("created_at"),
        )

    def get_latest_profile(self) -> Optional[RiskProfile]:
        sql = """
            SELECT id, age, horizon, reaction, risk_score, risk_label, created_at
            FROM risk_profiles
            ORDER BY id DESC
            LIMIT 1
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql)
            row = cursor.fetchone()

        if row is None:
            return None
        return self._row_to_profile(row)

    def save_profile(self, profile: RiskProfile) -> RiskProfile:
        sql = """
            INSERT INTO risk_profiles
                (age, horizon, reaction, risk_score, risk_label)
            VALUES (%s, %s, %s, %s, %s)
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (
                profile.age, profile.horizon, profile.reaction,
                profile.risk_score, profile.risk_label,
            ))
            profile_id = cursor.lastrowid

        return RiskProfile(
            id=profile_id,
            age=profile.age,
            horizon=profile.horizon,
            reaction=profile.reaction,
            risk_score=profile.risk_score,
            risk_label=profile.risk_label,
        )

    def get_all_profiles(self) -> List[RiskProfile]:
        sql = """
            SELECT id, age, horizon, reaction, risk_score, risk_label, created_at
            FROM risk_profiles
            ORDER BY id DESC
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql)
            rows = cursor.fetchall()

        return [self._row_to_profile(r) for r in rows]
