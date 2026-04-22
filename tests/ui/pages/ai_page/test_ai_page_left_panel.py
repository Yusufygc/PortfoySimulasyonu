import pytest
import sys
from PyQt5.QtWidgets import QApplication
from src.ui.pages.ai_page.left_panel.ticker_input_bar import TickerInputBar
from src.ui.pages.ai_page.left_panel.prediction_card import PredictionCard
from src.ui.pages.ai_page.left_panel.signal_card import SignalCard
from src.ui.pages.ai_page.core.models import Signal

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
    
    card.update_data("ASELS", 50.25, 0.85)
    assert "ASELS" in card.lbl_ticker.text()
    assert "50.25" in card.lbl_price.text()
    assert card.progress_conf.value() == 85
    
    card.reset()
    assert "Hisse: -" in card.lbl_ticker.text()
    assert card.progress_conf.value() == 0

def test_signal_card():
    """SignalCard veri güncellemesini ve sıfırlamasını test et."""
    card = SignalCard()
    
    card.update_data(Signal.BUY, 0.9)
    assert card.lbl_signal.text() == "AL"
    assert card.progress_strength.value() == 90
    
    card.reset()
    assert card.lbl_signal.text() == "-"
    assert card.progress_strength.value() == 0
