from __future__ import annotations

import json
import logging
from typing import Dict, Optional, List
from datetime import date
from urllib.request import Request, urlopen
import urllib.error
import urllib.parse
from config.settings_loader import load_market_settings
from src.domain.exceptions import MarketDataUnavailableError

logger = logging.getLogger(__name__)

class EvdsClient:
    def __init__(self, timeout: int = 10) -> None:
        self._timeout = timeout
        self._api_key = load_market_settings().evds_api_key or ""

    def get_series(self, series_code: str, start_date: date, end_date: date) -> List[Dict]:
        """
        Verilen seri kodu ve tarih araligi icin EVDS API'sinden veri ceker.
        """
        if not self._api_key:
            logger.warning("EVDS_API_KEY bulunamadi. EVDS API sorgusu yapilamayacak.")
            raise MarketDataUnavailableError("EVDS API_KEY tanimli degil.")
            
        start_str = start_date.strftime("%d-%m-%Y")
        end_str = end_date.strftime("%d-%m-%Y")
        
        # Ornek url format: https://evds3.tcmb.gov.tr/igmevdsms-dis/series=TP.KTF10&startDate=01-01-2023&endDate=31-12-2023&type=json
        url = f"https://evds3.tcmb.gov.tr/igmevdsms-dis/series={series_code}&startDate={start_str}&endDate={end_str}&type=json"
        
        request = Request(
            url,
            headers={
                "key": self._api_key,
                "Accept": "application/json"
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=self._timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
                return payload.get("items", [])
        except urllib.error.URLError as e:
            logger.error("EVDS API baglanti hatasi: %s", e)
            raise MarketDataUnavailableError(f"EVDS API baglanti hatasi: {e}") from e
