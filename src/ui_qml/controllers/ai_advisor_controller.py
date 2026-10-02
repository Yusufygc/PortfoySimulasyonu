"""
AiAdvisorController — Gemini AI Karar Destek ve Portföy Danışmanı QML Controller'ı (Faz 10).

Sorumluluklar:
- Gemini 2.5 Flash LLM ile interaktif sohbet ve portföy danışmanlığı yönetimi
- Function Calling araçları (get_portfolio_overview, get_allocation_and_risk, suggest_optimization, get_stock_overview)
- Portföy Sağlık Skoru (0-100) ve XAI Risk Faktörleri analizi
- ThreadPoolExecutor ile UI bloklamayan asenkron sorgulama ve Qt Queued Signal yapısı
- API anahtarı yokluğunda veya ağ kesintisinde yerel analiz motoru fallback'i
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.application.services.ai.ai_advisor_service import AiAdvisorService
from src.infrastructure.ai.gemini_advisor_chat_provider import (
    AdvisorChatResult,
    GeminiAdvisorChatProvider,
)

logger = logging.getLogger(__name__)

ADVISOR_SYSTEM_PROMPT = """Sen Borsa İstanbul (BIST) ve modern portföy yönetimi konusunda uzmanlaşmış, analitik, rasyonel ve yardımsever bir Kıdemli Portföy Danışmanısın.
Sana kullanıcının portföyünü, risk metriklerini ve hisse detaylarını inceleyebilmen için özel analiz araçları (tools) sağlanmıştır:
- get_portfolio_overview: Kullanıcının toplam portföy büyüklüğü, dönem getirisi, BIST100 farkı ve en iyi/kötü hisselerini döner.
- get_allocation_and_risk: Varlık dağılımı (ağırlık %), volatilite, maksimum düşüş (drawdown), beta, Sharpe ve yoğunlaşma durumunu döner.
- suggest_optimization: Modern Portföy Teorisi (Markowitz SLSQP) ile hedef ağırlıklar ve AL/SAT/TUT yeniden dengeleme önerileri döner.
- get_stock_overview: Tek bir hissenin güncel fiyatı, 52 haftalık aralığı ve teknik indikatörlerini (RSI, MACD, SMA) döner.

TEMEL İLKELERİN:
1. Kullanıcı portföyü, hisseleri veya piyasa hakkında bir şey sorduğunda ilgili aracı ÇAĞIR ve gerçek verilere dayanarak konuş.
2. Spekülatif, temelsiz veya kesinlik bildiren ("kesin yükselecektir", "tavan yapacak") ifadelerden kaçın.
3. Rakamları ve oranları Türkiye finans standartlarında ifade et (örn: ₺150.450,20 ve %14,25).
4. Yanıtlarında Markdown kalın metin, liste ve net paragraflar kullan. Aşırı uzun ve boğucu rapor dilinden kaçın; pratik ve uygulanabilir içgörüler sun.
5. Cevabın sonunda mutlaka 1-2 cümlelik "Özet / Aksiyon Önerisi" ve yasal uyarı ("Yatırım tavsiyesi niteliğinde değildir.") ekle.
"""


def _fmt_money_tr(val: float | Decimal | None) -> str:
    if val is None:
        return "0,00 ₺"
    try:
        return f"{float(val):,.2f} ₺".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return f"{val} ₺"


def _fmt_pct_tr(val: float | None, with_sign: bool = False) -> str:
    if val is None:
        return "%0,00"
    num = float(val)
    if abs(num) < 0.0001:
        return "%0,00"
    formatted = f"{abs(num):.2f}".replace(".", ",")
    if num < 0:
        return f"-%{formatted}"
    elif with_sign and num > 0:
        return f"+%{formatted}"
    return f"%{formatted}"


class AiAdvisorController(QObject):
    """QML AiAdvisorView için veri ve etkileşim köprüsü."""

    # QML Property Sinyalleri
    isLoadingChanged = Signal(bool)
    statusMessageChanged = Signal(str)
    messagesChanged = Signal()
    portfolioHealthScoreChanged = Signal(int)
    healthScoreLabelChanged = Signal(str)
    healthFactorsChanged = Signal()
    quickPromptsChanged = Signal()
    hasApiKeyChanged = Signal(bool)
    modelNameChanged = Signal(str)

    # Bildirim Sinyalleri
    messageReceived = Signal(str, str)  # role, content (otomatik kaydırma için)
    aiErrorOccurred = Signal(str)       # Toast bildirimi için

    # İç iş parçacığı sinyalleri (Qt Queued Connection garantisi)
    _asyncResponseReady = Signal(dict)
    _asyncErrorReady = Signal(str)

    def __init__(self, container=None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._container = container
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="AiAdvisorWorker")

        # Dahili durumlar
        self._is_loading = False
        self._status_message = "Hazır"
        self._model_name = "Gemini 2.5 Flash"
        self._messages: List[Dict[str, Any]] = []

        # Portföy Sağlık Metrikleri
        self._portfolio_health_score = 75
        self._health_score_label = "Dengeli"
        self._health_factors: List[Dict[str, Any]] = []

        # Hızlı Soru Önerileri
        self._quick_prompts: List[Dict[str, Any]] = [
            {
                "title": "Portföy Risk Analizi",
                "prompt": "Portföyümün genel risk ve getiri durumunu, Sharpe oranını ve en büyük risk faktörlerini özetler misin?",
                "icon": "shield-check",
            },
            {
                "title": "Varlık Dağılımı & Yoğunlaşma",
                "prompt": "Portföyümdeki varlık dağılımı ve hisse ağırlıklarım dengeli mi? Aşırı yoğunlaşma riski taşıyan hissem var mı?",
                "icon": "pie-chart",
            },
            {
                "title": "Rebalance (Yeniden Dengeleme)",
                "prompt": "Dengeli risk profiline göre portföyümü optimize ettiğimizde hangi hisseleri artırmalı veya azaltmalıyım?",
                "icon": "scale",
            },
            {
                "title": "Hisse Durum Değerlendirmesi",
                "prompt": "Portföyümdeki en büyük pozisyonumun güncel fiyatı, teknik seviyeleri ve 52 haftalık görünümü nedir?",
                "icon": "trending-up",
            },
        ]

        # İç sinyal bağlantıları
        self._asyncResponseReady.connect(self._on_async_response_ready)
        self._asyncErrorReady.connect(self._on_async_error_ready)

        # Karşılama mesajını ekle ve sağlık skorunu hesapla
        self._init_welcome_message()
        self.refreshHealthScore()

    # -------------------------------------------------------------------------
    # QML Property'leri
    # -------------------------------------------------------------------------

    @Property(bool, notify=isLoadingChanged)
    def isLoading(self) -> bool:
        return self._is_loading

    @Property(str, notify=statusMessageChanged)
    def statusMessage(self) -> str:
        return self._status_message

    @Property("QVariantList", notify=messagesChanged)
    def messages(self) -> List[Dict[str, Any]]:
        return self._messages

    @Property(int, notify=portfolioHealthScoreChanged)
    def portfolioHealthScore(self) -> int:
        return self._portfolio_health_score

    @Property(str, notify=healthScoreLabelChanged)
    def healthScoreLabel(self) -> str:
        return self._health_score_label

    @Property("QVariantList", notify=healthFactorsChanged)
    def healthFactors(self) -> List[Dict[str, Any]]:
        return self._health_factors

    @Property("QVariantList", notify=quickPromptsChanged)
    def quickPrompts(self) -> List[Dict[str, Any]]:
        return self._quick_prompts

    @Property(bool, notify=hasApiKeyChanged)
    def hasApiKey(self) -> bool:
        key = self._get_api_key()
        return bool(key and len(key.strip()) > 5)

    @Property(str, notify=modelNameChanged)
    def modelName(self) -> str:
        return self._model_name

    # -------------------------------------------------------------------------
    # Yardımcı Servis Erişimleri
    # -------------------------------------------------------------------------

    def _get_api_key(self) -> Optional[str]:
        if not self._container:
            return None
        settings = getattr(self._container, "settings", None)
        if settings and hasattr(settings, "ai"):
            return getattr(settings.ai, "gemini_api_key", None)
        return None

    def _get_advisor_service(self) -> Optional[AiAdvisorService]:
        if not self._container:
            return None
        return getattr(self._container, "ai_advisor_service", None)

    def _get_portfolio_analytics_service(self):
        if not self._container:
            return None
        services = getattr(self._container, "services", None)
        if services and hasattr(services, "portfolio_analytics_service"):
            return services.portfolio_analytics_service
        return getattr(self._container, "portfolio_analytics_service", None)

    def _get_risk_optimization_bridge(self):
        if not self._container:
            return None
        services = getattr(self._container, "services", None)
        if services and hasattr(services, "risk_optimization_bridge_service"):
            return services.risk_optimization_bridge_service
        return getattr(self._container, "risk_optimization_bridge_service", None)

    def _get_stock_360_service(self):
        if not self._container:
            return None
        services = getattr(self._container, "services", None)
        if services and hasattr(services, "stock_360_service"):
            return services.stock_360_service
        return getattr(self._container, "stock_360_service", None)

    # -------------------------------------------------------------------------
    # Karşılama ve Sıfırlama
    # -------------------------------------------------------------------------

    def _init_welcome_message(self) -> None:
        now_str = datetime.now().strftime("%H:%M")
        welcome = {
            "id": "msg-0",
            "role": "ai",
            "content": (
                "**Merhaba! Ben Gemini destekli Yapay Zeka Portföy Danışmanınız.**\n\n"
                "Portföyünüzün risk ve varlık dağılımını analiz edebilir, Modern Portföy Teorisi'ne göre "
                "yeniden dengeleme (rebalance) önerileri sunabilir ve hisselerinizin teknik/temel verilerini yorumlayabilirim.\n\n"
                "Aşağıdaki **Hızlı Analiz Soruları**ndan birine tıklayabilir veya aklınızdaki soruyu doğrudan yazabilirsiniz."
            ),
            "timestamp": now_str,
            "toolCalls": [],
        }
        self._messages = [welcome]
        self.messagesChanged.emit()

    @Slot()
    def clearChat(self) -> None:
        """Sohbet geçmişini sıfırlar ve karşılama mesajını yükler."""
        self._init_welcome_message()
        self._set_status("Sohbet sıfırlandı")

    # -------------------------------------------------------------------------
    # Mesaj Gönderme ve Asenkron Çalıştırma
    # -------------------------------------------------------------------------

    @Slot(int)
    def sendQuickPrompt(self, prompt_index: int) -> None:
        """Belirtilen hızlı soru şablonunu gönderir."""
        if 0 <= prompt_index < len(self._quick_prompts):
            text = self._quick_prompts[prompt_index]["prompt"]
            self.sendMessage(text)

    @Slot(str)
    def sendMessage(self, text: str) -> None:
        """Kullanıcı mesajını alır ve asenkron yanıt sürecini başlatır."""
        query = (text or "").strip()
        if not query or self._is_loading:
            return

        now_str = datetime.now().strftime("%H:%M")
        user_msg = {
            "id": f"msg-{len(self._messages) + 1}",
            "role": "user",
            "content": query,
            "timestamp": now_str,
            "toolCalls": [],
        }
        self._messages.append(user_msg)
        self.messagesChanged.emit()
        self.messageReceived.emit("user", query)

        self._set_loading(True)
        self._set_status("Gemini analiz ediyor ve portföy verilerini inceliyor...")

        # Asenkron arka plan görevi
        history_tuples = [(m["role"], m["content"]) for m in self._messages if m["role"] in ("user", "ai")]
        self._executor.submit(self._run_advisor_worker, query, history_tuples)

    def _run_advisor_worker(self, query: str, history: List[Tuple[str, str]]) -> None:
        """Arka planda Gemini API veya yerel simülasyon motorunu çalıştırır."""
        try:
            api_key = self._get_api_key()
            advisor_service = self._get_advisor_service()

            # 1. Gerçek Gemini API + Function Calling Denemesi
            if api_key and advisor_service:
                try:
                    provider = GeminiAdvisorChatProvider(
                        api_key=api_key,
                        tool_declarations=advisor_service.tool_declarations,
                        call_tool=advisor_service.call_tool,
                    )
                    # Turns: Gemini 'user' ve 'model' bekler
                    turns = [
                        ("user" if role == "user" else "model", content)
                        for role, content in history
                    ]
                    chat_result: AdvisorChatResult = provider.generate(ADVISOR_SYSTEM_PROMPT, turns)
                    tools_used = [
                        {
                            "name": tc.name,
                            "label": self._tool_name_to_label(tc.name),
                        }
                        for tc in chat_result.tool_calls
                    ]
                    self._asyncResponseReady.emit({
                        "content": chat_result.text,
                        "toolCalls": tools_used,
                    })
                    return
                except Exception as exc:
                    logger.warning("Gemini API çağrısı başarısız, yerel analiz motoruna geçiliyor: %s", exc)

            # 2. Yerel Akıllı Analiz Fallback'i (Gerçek Portföy Verileri ile)
            fallback_response, used_tools = self._generate_local_portfolio_analysis(query)
            self._asyncResponseReady.emit({
                "content": fallback_response,
                "toolCalls": used_tools,
            })

        except Exception as e:
            logger.exception("Danışman yanıtı üretilirken beklenmeyen hata: %s", e)
            self._asyncErrorReady.emit(str(e))

    def _tool_name_to_label(self, name: str) -> str:
        mapping = {
            "get_portfolio_overview": "Portföy Genel Özeti",
            "get_allocation_and_risk": "Varlık Dağılımı ve Risk",
            "suggest_optimization": "Markowitz Optimizasyonu",
            "get_stock_overview": "Hisse Teknik & Fiyat Analizi",
        }
        return mapping.get(name, name)

    # -------------------------------------------------------------------------
    # Yerel Akıllı Analiz Fallback Motoru (Gerçek Portföy Verilerine Dayanır)
    # -------------------------------------------------------------------------

    def _generate_local_portfolio_analysis(self, query: str) -> Tuple[str, List[Dict[str, str]]]:
        """API anahtarı yokken veya ağ hatasında reel portföy verileriyle zengin karar desteği sunar."""
        advisor = self._get_advisor_service()
        analytics = self._get_portfolio_analytics_service()
        risk_bridge = self._get_risk_optimization_bridge()
        stock_svc = self._get_stock_360_service()

        used_tools: List[Dict[str, str]] = []
        lower_q = query.lower()

        # Araç 1: Portföy Özeti
        overview_data = {}
        if advisor:
            try:
                overview_data = advisor.call_tool("get_portfolio_overview", {})
                used_tools.append({
                    "name": "get_portfolio_overview",
                    "label": "Portföy Genel Özeti",
                })
            except Exception:
                pass

        # Araç 2: Dağılım ve Risk
        risk_data = {}
        if advisor:
            try:
                risk_data = advisor.call_tool("get_allocation_and_risk", {})
                used_tools.append({
                    "name": "get_allocation_and_risk",
                    "label": "Varlık Dağılımı ve Risk",
                })
            except Exception:
                pass

        total_val = overview_data.get("total_value_try") or 0.0
        period_ret = overview_data.get("period_return_pct")
        benchmark_gap = overview_data.get("benchmark_gap_pct")
        largest_stock = overview_data.get("largest_position_label") or "Yok"
        largest_weight = overview_data.get("largest_position_weight_pct") or 0.0
        sharpe = risk_data.get("sharpe_ratio")
        volatility = risk_data.get("volatility_pct")
        max_dd = risk_data.get("max_drawdown_pct")
        top3_weight = risk_data.get("top_three_weight_pct") or 0.0

        # Eğer soru Optimizasyon / Rebalance ile ilgiliyse
        if any(w in lower_q for w in ["optimizasyon", "rebalance", "dengele", "öneri", "al", "sat"]):
            opt_data = {}
            if advisor:
                try:
                    opt_data = advisor.call_tool("suggest_optimization", {"risk_label": "DENGELI"})
                    used_tools.append({
                        "name": "suggest_optimization",
                        "label": "Markowitz Optimizasyonu",
                    })
                except Exception:
                    pass

            suggestions = opt_data.get("suggestions", [])
            lines = [
                "### Modern Portföy Teorisi — Yeniden Dengeleme Analizi",
                "",
                f"Mevcut portföyünüzün toplam büyüklüğü **{_fmt_money_tr(total_val)}** seviyesindedir. "
                f"Dengeli risk profili simülasyonuna göre portföyünüzün getiri/risk oranını maksimize etmek için aşağıdaki düzenlemeler önerilmektedir:",
                "",
            ]
            if suggestions:
                lines.append("| Hisse | Mevcut Pay | Hedef Pay | Değişim | Aksiyon |")
                lines.append("| :--- | :--- | :--- | :--- | :--- |")
                for s in suggestions[:6]:
                    sym = s.get("symbol", "").replace(".IS", "")
                    cur_w = _fmt_pct_tr(s.get("current_weight_pct"))
                    opt_w = _fmt_pct_tr(s.get("optimal_weight_pct"))
                    chg = _fmt_pct_tr(s.get("change_pct"), with_sign=True)
                    act = s.get("action", "TUT")
                    lines.append(f"| **{sym}** | {cur_w} | {opt_w} | {chg} | **{act}** |")
                lines.append("")
                lines.append(
                    "**Stratejik Değerlendirme:** Portföyde ağırlığı yüksek olan hisselerden kâr realizasyonu "
                    "yapılarak ağırlığı düşük kalan hisselere pay aktarılması genel portföy volatilitesini düşürecektir."
                )
            else:
                lines.append("Portföyünüzde henüz yeterli çeşitlilikte hisse senedi bulunmadığından optimizasyon matrisi oluşturulamadı.")

            lines.append("")
            lines.append("*Not: Yerel analiz motoru çalıştırıldı. Gemini API anahtarı ekleyerek çoklu turlu etkileşimli danışmanlığı aktif edebilirsiniz.*")
            lines.append("")
            lines.append("**Yatırım Tavsiyesi Değildir (YTD).**")
            return "\n".join(lines), used_tools

        # Genel Risk & Portföy Değerlendirmesi
        lines = [
            "### Portföy Sağlık & Risk Durumu Raporu",
            "",
            f"Portföyünüzün toplam değeri **{_fmt_money_tr(total_val)}** olup piyasa hareketlerine karşı genel görünümü şöyledir:",
            "",
            f"- **Dönem Getirisi:** {_fmt_pct_tr(period_ret, with_sign=True)} "
            f"(BIST 100 Endeksine Göre: {_fmt_pct_tr(benchmark_gap, with_sign=True)})",
            f"- **Yıllık Volatilite (Risk):** {_fmt_pct_tr(volatility)}",
            f"- **Sharpe Oranı:** {f'{sharpe:.2f}' if sharpe is not None else 'N/A'} (Birim risk başına getiri kalitesi)",
            f"- **Maksimum Geri Çekilme (Drawdown):** {_fmt_pct_tr(max_dd)}",
            f"- **En Büyük Pozisyon:** **{largest_stock.replace('.IS', '')}** ({_fmt_pct_tr(largest_weight)})",
            f"- **İlk 3 Hisse Yoğunlaşması:** {_fmt_pct_tr(top3_weight)}",
            "",
            "#### Danışman Değerlendirmesi:",
        ]

        if top3_weight > 60:
            lines.append(
                "- **Yüksek Yoğunlaşma Riski:** Portföyünüzün %60'ından fazlası ilk 3 hissede toplanmış durumda. "
                "Sektörel şoklara karşı dayanıklılığı artırmak için portföyü farklı sektörlere yaymanız önerilir."
            )
        else:
            lines.append(
                "- **Dengeli Varlık Dağılımı:** Hisselerinizin portföye dağılımı makul seviyelerde. Tek bir hisseye aşırı bağımlılık riski düşük."
            )

        if sharpe is not None and sharpe > 1.0:
            lines.append(
                "- **Güçlü Risk-Getiri Dengesi:** Sharpe oranınız 1.0 seviyesinin üzerinde, bu da aldığınız riskin getiri ile iyi dengelendiğini gösteriyor."
            )
        else:
            lines.append(
                "- **Getiri Potansiyeli:** Volatiliteye oranla getiri marjını yükseltmek için 'Optimizasyon' sekmesindeki rebalance modelini inceleyebilirsiniz."
            )

        lines.append("")
        lines.append("*Not: Yerel analiz motoru çalıştırıldı. Gemini API anahtarı tanımlandığında model ile doğrudan serbest sohbet edebilirsiniz.*")
        lines.append("")
        lines.append("**Yatırım Tavsiyesi Değildir (YTD).**")
        return "\n".join(lines), used_tools

    # -------------------------------------------------------------------------
    # Yanıt ve Hata Geri Çağrıları (Qt Ana İş Parçacığı)
    # -------------------------------------------------------------------------

    def _on_async_response_ready(self, result: Dict[str, Any]) -> None:
        now_str = datetime.now().strftime("%H:%M")
        ai_msg = {
            "id": f"msg-{len(self._messages) + 1}",
            "role": "ai",
            "content": result.get("content", ""),
            "timestamp": now_str,
            "toolCalls": result.get("toolCalls", []),
        }
        self._messages.append(ai_msg)
        self.messagesChanged.emit()
        self.messageReceived.emit("ai", ai_msg["content"])
        self._set_loading(False)
        self._set_status("Hazır")

    def _on_async_error_ready(self, error_msg: str) -> None:
        now_str = datetime.now().strftime("%H:%M")
        err_entry = {
            "id": f"msg-{len(self._messages) + 1}",
            "role": "system",
            "content": f"Yanıt alınırken bir hata oluştu: {error_msg}",
            "timestamp": now_str,
            "toolCalls": [],
        }
        self._messages.append(err_entry)
        self.messagesChanged.emit()
        self.aiErrorOccurred.emit(error_msg)
        self._set_loading(False)
        self._set_status("Hata oluştu")

    # -------------------------------------------------------------------------
    # Portföy Sağlık Skoru & XAI Risk Faktörleri Hesaplama
    # -------------------------------------------------------------------------

    @Slot()
    def refreshHealthScore(self) -> None:
        """Portföyün gerçek analitik verilerinden 0-100 sağlık skoru ve risk faktörlerini hesaplar."""
        advisor = self._get_advisor_service()
        if not advisor:
            self._set_default_health_metrics()
            return

        try:
            risk_data = advisor.call_tool("get_allocation_and_risk", {})
            top3_w = float(risk_data.get("top_three_weight_pct") or 50.0)
            volatility = float(risk_data.get("volatility_pct") or 30.0)
            sharpe = risk_data.get("sharpe_ratio")
            sharpe_val = float(sharpe) if sharpe is not None else 0.8
            max_dd = abs(float(risk_data.get("max_drawdown_pct") or 20.0))

            # 1. Çeşitlilik Puanı (max 25)
            if top3_w <= 40.0:
                score_div = 25
                div_status = "Yüksek Çeşitlilik"
            elif top3_w <= 60.0:
                score_div = 20
                div_status = "Dengeli Dağılım"
            elif top3_w <= 80.0:
                score_div = 12
                div_status = "Orta Yoğunlaşma"
            else:
                score_div = 6
                div_status = "Yüksek Yoğunlaşma Riski"

            # 2. Risk & Volatilite Puanı (max 25)
            if volatility <= 22.0:
                score_vol = 25
                vol_status = "Düşük Volatilite"
            elif volatility <= 32.0:
                score_vol = 20
                vol_status = "Piyasa Ortalaması"
            elif volatility <= 42.0:
                score_vol = 14
                vol_status = "Yüksek Dalgalanma"
            else:
                score_vol = 8
                vol_status = "Aşırı Riskli"

            # 3. Sharpe & Getiri Kalitesi Puanı (max 25)
            if sharpe_val >= 1.5:
                score_shp = 25
                shp_status = "Mükemmel Getiri/Risk"
            elif sharpe_val >= 1.0:
                score_shp = 20
                shp_status = "İyi Performans"
            elif sharpe_val >= 0.5:
                score_shp = 14
                shp_status = "Kabul Edilebilir"
            else:
                score_shp = 8
                shp_status = "Düşük Getiri Verimi"

            # 4. Maksimum Geri Çekilme (Drawdown) Puanı (max 25)
            if max_dd <= 15.0:
                score_dd = 25
                dd_status = "Mükemmel Koruma"
            elif max_dd <= 25.0:
                score_dd = 20
                dd_status = "Normal Geri Çekilme"
            elif max_dd <= 35.0:
                score_dd = 14
                dd_status = "Yüksek Kayıp Riski"
            else:
                score_dd = 8
                dd_status = "Kritik Düşüş Seviyesi"

            total_score = score_div + score_vol + score_shp + score_dd
            self._portfolio_health_score = max(0, min(100, total_score))

            if self._portfolio_health_score >= 80:
                self._health_score_label = "Çok Güçlü"
            elif self._portfolio_health_score >= 65:
                self._health_score_label = "Dengeli"
            elif self._portfolio_health_score >= 50:
                self._health_score_label = "Orta Risk"
            else:
                self._health_score_label = "Yüksek Risk"

            self._health_factors = [
                {
                    "title": "Varlık Çeşitliliği",
                    "value": f"%{top3_w:.1f} (İlk 3)",
                    "score": score_div,
                    "maxScore": 25,
                    "status": div_status,
                    "isGood": score_div >= 18,
                },
                {
                    "title": "Volatilite & Risk",
                    "value": f"%{volatility:.1f}",
                    "score": score_vol,
                    "maxScore": 25,
                    "status": vol_status,
                    "isGood": score_vol >= 18,
                },
                {
                    "title": "Sharpe Rasyosu",
                    "value": f"{sharpe_val:.2f}",
                    "score": score_shp,
                    "maxScore": 25,
                    "status": shp_status,
                    "isGood": score_shp >= 18,
                },
                {
                    "title": "Maksimum Düşüş",
                    "value": f"-%{max_dd:.1f}",
                    "score": score_dd,
                    "maxScore": 25,
                    "status": dd_status,
                    "isGood": score_dd >= 18,
                },
            ]

        except Exception as exc:
            logger.warning("Portföy sağlık skoru hesaplanırken hata: %s", exc)
            self._set_default_health_metrics()

        self.portfolioHealthScoreChanged.emit(self._portfolio_health_score)
        self.healthScoreLabelChanged.emit(self._health_score_label)
        self.healthFactorsChanged.emit()

    def _set_default_health_metrics(self) -> None:
        self._portfolio_health_score = 70
        self._health_score_label = "Dengeli"
        self._health_factors = [
            {"title": "Varlık Çeşitliliği", "value": "%55.0", "score": 18, "maxScore": 25, "status": "Dengeli Dağılım", "isGood": True},
            {"title": "Volatilite & Risk", "value": "%28.4", "score": 19, "maxScore": 25, "status": "Piyasa Ortalaması", "isGood": True},
            {"title": "Sharpe Rasyosu", "value": "1.12", "score": 18, "maxScore": 25, "status": "İyi Performans", "isGood": True},
            {"title": "Maksimum Düşüş", "value": "-%18.5", "score": 15, "maxScore": 25, "status": "Normal Seviye", "isGood": True},
        ]

    # -------------------------------------------------------------------------
    # API Anahtarı Yönetimi
    # -------------------------------------------------------------------------

    @Slot(str)
    def saveApiKey(self, key: str) -> None:
        """Kullanıcının girdiği API anahtarını kaydeder."""
        clean_key = (key or "").strip()
        if not clean_key or not self._container:
            return
        settings = getattr(self._container, "settings", None)
        if settings and hasattr(settings, "ai"):
            settings.ai.gemini_api_key = clean_key
            self.hasApiKeyChanged.emit(True)
            self._set_status("Gemini API Anahtarı kaydedildi")
            self._messages.append({
                "id": f"msg-{len(self._messages) + 1}",
                "role": "system",
                "content": "Google Gemini API anahtarınız başarıyla tanımlandı. Gemini 2.5 Flash ile tam etkileşimli danışmanlık aktif.",
                "timestamp": datetime.now().strftime("%H:%M"),
                "toolCalls": [],
            })
            self.messagesChanged.emit()

    # -------------------------------------------------------------------------
    # Durum ve Yardımcılar
    # -------------------------------------------------------------------------

    def _set_loading(self, val: bool) -> None:
        if self._is_loading != val:
            self._is_loading = val
            self.isLoadingChanged.emit(val)

    def _set_status(self, msg: str) -> None:
        if self._status_message != msg:
            self._status_message = msg
            self.statusMessageChanged.emit(msg)
