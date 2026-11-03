"""Haber konu süzgeci: Türkçe harf katlama, önek/tam kelime eşleşmesi ve magazin engeli."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.application.services.news.news_relevance import is_blocked, is_on_topic
from src.domain.models.news_item import NewsItem


def _item(title: str, summary: str = "") -> NewsItem:
    return NewsItem(title=title, url="https://ex.com/x", source_id="s", source_name="s",
                    published_at=datetime(2026, 11, 1, tzinfo=timezone.utc), summary=summary)


@pytest.mark.parametrize("title", [
    "BORSA İSTANBUL güne yükselişle başladı",
    "Merkez Bankası faiz kararını açıkladı",
    "Cumhurbaşkanı kabine toplantısı sonrası konuştu",
    "Dışişleri Bakanı Rus mevkidaşıyla görüştü: ateşkes",
    "Fed holds rates as inflation cools",
    "Oil prices climb on Middle East talks",
    "Ukrayna ile barış müzakereleri sürüyor",
])
def test_on_topic(title):
    assert is_on_topic(_item(title))


@pytest.mark.parametrize("title,summary", [
    ("Ünlü şarkıcı sevgilisiyle görüntülendi", "magazin"),
    ("Hava durumu: hafta sonu sağanak", ""),
    ("Federal courts reopen after storm", ""),   # `fed$` tam kelime: "federal" eşleşmez
    ("Kızıl halıda şıklık yarışı", "celebrity"),
])
def test_off_topic(title, summary):
    assert not is_on_topic(_item(title, summary))


def test_gossip_blocks_even_when_topic_word_present():
    item = _item("Ünlü manken borsa yatırımı yaptı", "magazin haberi")
    assert is_blocked(item) and not is_on_topic(item)


def test_turkish_dotted_capital_i_folds():
    assert is_on_topic(_item("İHRACAT rekora koştu"))
    assert is_on_topic(_item("YATIRIMCILAR temkinli"))
