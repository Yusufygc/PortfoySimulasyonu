from abc import ABC, abstractmethod
import random
from src.ui.pages.ai_page.core.models import AnalysisResult, Signal

class AIModelInterface(ABC):
    @abstractmethod
    def analyze(self, ticker: str) -> AnalysisResult:
        """Senkron çağrı. QThread içinde çalıştırılacak."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Model/process erişilebilir mi? UI banner için."""
        pass

class MockAdapter(AIModelInterface):
    """
    Gerçek model hazır olana kadar kullanılacak.
    Gerçekçi rastgele veri üretir.
    is_available() → False döner → UI'da sarı uyarı gösterir.
    """
    def analyze(self, ticker: str) -> AnalysisResult:
        # Demo veriler oluştur
        price = random.uniform(10.0, 500.0)
        conf = random.uniform(0.5, 0.95)
        signals = list(Signal)
        sig = random.choice(signals)
        strength = random.uniform(0.4, 0.9)
        
        return AnalysisResult(
            ticker=ticker,
            predicted_price=round(price, 2),
            confidence=round(conf, 2),
            signal=sig,
            signal_strength=round(strength, 2),
            xai_features={
                "RSI": round(random.uniform(0.1, 0.9), 2), 
                "MACD": round(random.uniform(0.1, 0.9), 2), 
                "Volume": round(random.uniform(0.1, 0.9), 2)
            },
            xai_text="Demo: Bu hisse için teknik göstergeler karışık bir tablo çiziyor. Modelin tahmini referans amaçlıdır ve gerçek bir model bağlandığında güncellenecektir."
        )

    def is_available(self) -> bool:
        return False
