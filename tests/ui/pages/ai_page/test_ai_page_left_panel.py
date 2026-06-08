import pytest
import sys
pytest.importorskip("PyQt5")
from PyQt5.QtWidgets import QApplication, QLabel
from src.ui.pages.ai_page.left_panel.ticker_input_bar import TickerInputBar
from src.ui.pages.ai_page.left_panel.prediction_card import PredictionCard
from src.ui.pages.ai_page.left_panel.signal_card import SignalCard
from src.ui.pages.ai_page.left_panel.xai_card import XAICard
from src.domain.models.ai_analysis import ModelOutlook, XaiFactorItem

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

def test_ticker_input_bar():
    """TickerInputBar arayüzünün doğru çalıştığını test et."""
    bar = TickerInputBar()
    
    assert bar.btn_analyze.isEnabled() == False
    
    bar.input_field.setText("thyao")
    assert bar.input_field.text() == "THYAO"
    assert bar.btn_analyze.isEnabled() == True
    
    bar.input_field.setText("")
    assert bar.btn_analyze.isEnabled() == False

def test_prediction_card():
    """PredictionCard veri güncellemesini ve sıfırlamasını test et."""
    card = PredictionCard()
    
    card.update_data("ASELS", 50.25, 0.85, horizon_days=5, weekly_expected_return=0.025)
    assert "ASELS" in card.lbl_ticker.text()
    assert "50.25" in card.lbl_price.text()
    assert "5" in card.lbl_return.text()
    assert "Bile" in card.lbl_return.text()
    assert card.progress_conf.value() == 85
    
    card.reset()
    assert "Hisse: -" in card.lbl_ticker.text()
    assert card.progress_conf.value() == 0

def test_signal_card():
    """Yön beklentisi kartı emir dili kullanmadan güncellenir."""
    card = SignalCard()
    
    card.update_data(ModelOutlook.UP, 0.9)
    assert card.lbl_signal.text() == "Yükseliş Eğilimi"
    assert card.progress_strength.value() == 90
    
    card.reset()
    assert card.lbl_signal.text() == "-"
    assert card.progress_strength.value() == 0


def test_xai_card_renders_factor_details():
    """XAICard faktör grubu ve reason detaylarını kesmeden widget ağacına ekler."""
    card = XAICard()
    card.update_data(
        features={},
        text="XAI özeti",
        xai_available=True,
        xai_method="Feature Importance",
        positive_reasons=[
            XaiFactorItem(
                feature_name="RSI_14",
                human_label="RSI 14: aşırı alım/satım sinyali",
                importance=0.68,
                direction="positive",
                feature_group="technical",
                reason="RSI 14 momentum tarafındaki kısa vadeli güçlenmeyi gösterdi.",
                method="sequence",
                contribution=0.12,
                approximate=True,
            )
        ],
        negative_reasons=[],
        xai_caveat="Nedensellik kanıtı değildir.",
    )

    labels = [label.text() for label in card.findChildren(QLabel)]
    assert any("RSI 14" in text for text in labels)
    assert any("Grafik" in text for text in labels)
    assert any("momentum" in text for text in labels)


def test_peer_card_without_pooled_price():
    """PeerCard updates with basic peer info but hides pooled price if missing."""
    from src.ui.pages.ai_page.left_panel.peer_card import PeerCard
    from src.domain.models.ai_analysis import PeerInfo

    card = PeerCard()
    peer = PeerInfo(
        available=True,
        as_of_date="2026-06-08",
        peer_percentile=92.0,
        peer_label="outperform",
        universe_size=100,
        segment_liq="High",
        segment_vol="Medium",
        segment_sector="Finans",
        trend_label="Yükseliş",
        trend_prob_up=0.55,
        trend_expected_return=0.015,
        confidence_label="high",
        xai_available=False
    )
    card.update_data(peer)
    assert card.isVisible() is True
    assert "92" in card.lbl_rank.text()
    assert card.lbl_pooled_price.isVisible() is False


def test_peer_card_with_pooled_price():
    """PeerCard updates and shows pooled price when all Kol-B fields are present."""
    from src.ui.pages.ai_page.left_panel.peer_card import PeerCard
    from src.domain.models.ai_analysis import PeerInfo

    card = PeerCard()
    peer = PeerInfo(
        available=True,
        as_of_date="2026-06-08",
        peer_percentile=92.0,
        peer_label="outperform",
        universe_size=100,
        segment_liq="High",
        segment_vol="Medium",
        segment_sector="Finans",
        trend_label="Yükseliş",
        trend_prob_up=0.55,
        trend_expected_return=0.015,
        confidence_label="high",
        kolb_price_p50=105.50,
        kolb_price_low=98.20,
        kolb_price_high=112.80,
        kolb_horizon_days=5,
        kolb_band_level=0.8,
        xai_available=False
    )
    card.update_data(peer)
    assert card.isVisible() is True
    assert "92" in card.lbl_rank.text()
    assert card.lbl_pooled_price.isVisible() is True
    assert "105.50" in card.lbl_pooled_price.text()
    assert "98.20" in card.lbl_pooled_price.text()
    assert "112.80" in card.lbl_pooled_price.text()
    assert "5g" in card.lbl_pooled_price.text()

    card.reset()
    assert card.lbl_pooled_price.isVisible() is False
    assert card.isVisible() is False

