from __future__ import annotations

import json
import logging
from typing import Dict
from urllib.request import Request, urlopen
import urllib.error
from src.domain.exceptions import MarketDataUnavailableError

logger = logging.getLogger(__name__)

USER_AGENT_WINDOWS_CHROME = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

class EvdsClient:
    def __init__(self, timeout: int = 10) -> None:
        self._timeout = timeout

    def request_json_post(self, url: str, payload: Dict[str, object]):
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "User-Agent": USER_AGENT_WINDOWS_CHROME,
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json;charset=UTF-8",
                "Origin": "https://evds3.tcmb.gov.tr",
                "Referer": "https://evds3.tcmb.gov.tr/",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as e:
            logger.error("EVDS API baglanti hatasi: %s", e)
            raise MarketDataUnavailableError(f"EVDS API baglanti hatasi: {e}") from e

    def request_json_post_path(self, path: str, payload: Dict[str, object]):
        return self.request_json_post(f"https://evds3.tcmb.gov.tr/igmevdsms-dis{path}", payload)
