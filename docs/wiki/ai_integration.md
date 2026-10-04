# Yapay Zeka Entegrasyonu

> Ana sayfa: [index.md](index.md) | Mimari: [architecture.md](architecture.md) | Sayfa: [qml_pages_guide.md](qml_pages_guide.md)

Yapay zeka özellikleri üç ayrı yoldan gelir ve hepsi **yatırım tavsiyesi vermeyen** analiz/yorum aracıdır:

| Özellik | Sağlayıcı | Nerede |
|---|---|---|
| **Portföy Danışmanı** (function-calling sohbet) | Gemini 2.5 Flash (`GeminiAdvisorChatProvider`) | AI Asistan sayfası, mod "Portföy Danışmanı" |
| **Hisse Modeli** (tahmin, XAI, akran) | AI_Core FastAPI servisi, kapalıysa demo | AI Asistan sayfası, mod "Hisse Modeli" |
| **Karşılaştırma yorumu** | Gemini (`GeminiChatProvider`, `gemini-3-flash-preview`) | Karşılaştırma Lab > Yapay Zeka Yorumu |

API anahtarı `GEMINI_API_KEY` (veya Ayarlar > API Anahtarları) ile verilir; `AI_CORE_API_URL` AI_Core adresidir.

## 1. Katmanlar

| Katman | Bileşen |
|---|---|
| Domain | `models/ai_analysis.py` (`AnalysisResult`, `ModelOutlook`, `ForecastPoint`, `XaiFactorItem`, `PeerInfo`, `ChatMessage`, `MessageRole`), `models/ai_tool.py` (`ToolDeclaration`); portlar `i_ai_chat_provider`, `i_ai_analysis_provider`, `i_chat_history_repo`. |
| Application (`services/ai/`) | `AiAdvisorService` (araç kayıt defteri ve sohbet), `advisor_tools.py`, `AiChatService`, `AiAnalysisService`, `ChatSessionService`, `safety_guard.py`. |
| Infrastructure (`infrastructure/ai/`) | `GeminiAdvisorChatProvider`, `GeminiChatProvider`, `AICoreFastAPIClient` + `FastAPIAnalysisProvider`, `MockAIAnalysisProvider`, `QSettingsChatHistoryRepository`. |
| UI | `AiAdvisorController`, `ModelAnalysisController`; `AiAdvisorView.qml`, `ModelAnalysisPanel.qml`, `ChatHistoryDialog.qml`. |

`container_parts/ai.py::build_ai` bunları kurar; `AiAdvisorService` Gemini sağlayıcısını `chat_provider_factory` ile alır (denetleyici SDK'yı doğrudan import etmez).

## 2. Portföy Danışmanı (Tool-Calling)

Kod yapısı (UI katmanı): `ai_advisor_controller.py` QML yüzeyi ve sinyal akışını; `advisor_chat_support.py` sistem istemi, karşılama, hızlı sorular, oturum dönüşümleri ve Gemini çağrısını; `advisor_local_analysis.py` anahtar yokken çalışan yerel analiz motorunu; `advisor_health.py` sağlık skoru eşik tablolarını ve hesabını taşır.

Akış: kullanıcı mesajı -> `AiAdvisorController` arka plan iş parçacığında `AiAdvisorService.chat(api_key, sistem_istemi, turlar)` -> `GeminiAdvisorChatProvider` Gemini'ye araç bildirimleriyle gönderir -> model araç çağırırsa servis çalıştırıp sonucu geri verir -> en çok **4 tur** sonra son metin döner. Sonuç metin ve "kullanılan araçlar" rozetleri olarak gösterilir.

Araçlar (`advisor_tools.py`; hepsi **salt okunur**, JSON döner; mutasyon aracı eklenmez ve bu bir istem kuralı değil mimari sınırdır):

| Araç | Kaynak |
|---|---|
| `get_portfolio_overview` | `PortfolioAnalyticsService.get_overview`: toplam değer, dönem getirisi, BIST 100 farkı, en iyi/kötü katkı. |
| `get_allocation_and_risk` | `get_allocation_risk_view`: ağırlıklar, volatilite, maksimum düşüş, beta, Sharpe, yoğunlaşma. |
| `suggest_optimization(risk_label?)` | `RiskOptimizationBridgeService`: Markowitz hedef ağırlıklar ve EKLE/AZALT/TUT önerileri ([service_planning_optimization.md](service_planning_optimization.md)). |
| `get_stock_overview(ticker)` | `Stock360Service`: fiyat, 52 hafta aralığı, RSI/MACD/SMA ([stock_360.md](stock_360.md)). |

Bilinmeyen araç adı veya araç içi hata exception fırlatmaz; `{"error": ...}` döner ve sohbet çökmez.

**Geri düşme:** API anahtarı yoksa veya Gemini çağrısı hata verirse denetleyici gerçek portföy verisiyle çalışan **yerel analiz motoruna** düşer (aynı araçları doğrudan çağırıp şablonla yanıt üretir); durum çubuğu "Simülasyon" rozetiyle belirtir. Anahtar varsa "Çevrimiçi".

**Portföy Sağlık Skoru (0-100)** her yenilemede hesaplanır: dört boyut, her biri en çok 25 puan: varlık çeşitliliği (ilk üç pozisyon ağırlığı), volatilite, Sharpe, maksimum düşüş. Etiketler: >= 80 Çok Güçlü, >= 65 Dengeli, >= 50 Orta Risk, altı Yüksek Risk. Sağ panelde boyut çubukları ("XAI içgörüleri") gösterilir; hesap hata verirse varsayılan skor 70 gösterilir.

**Hızlı sorular:** dört hazır istem çipi güvenilir yol (`sendMessage`) üzerinden gider.

**Sohbet geçmişi:** `ChatSessionService` oturumları listeler, devam ettirir, siler; yeni oturum ilk kullanıcı mesajı gelene dek kaydedilmez, başlık ilk mesajdan türetilir. Oturumlar `QSettings`'te tutulur (`QSettingsChatHistoryRepository`), veritabanında değil. Uygulama her açılışta son oturumu geri yükler.

## 3. Girdi Güvenliği (`safety_guard.py`)

`submitUserMessage(text)` (kullanıcının yazdığı mesaj) göndermeden önce `validate_user_input` çalıştırır:

- En çok **750 karakter** (`MAX_CHAR_LIMIT`; giriş kutusu `maximumLength` ile sınırlıdır).
- `config/safety_patterns.txt` içindeki regex kalıpları (İngilizce ve Türkçe prompt-injection/jailbreak ifadeleri, kod yazma talepleri, "yatırım tavsiyesi ver" gibi kapsam dışı istekler; büyük/küçük harf duyarsız). Dosya okunamazsa gömülü yedek liste kullanılır.
- Riskli girdi reddedilir ve kullanıcıya "Güvenlik Uyarısı" gösterilir; model çağrılmaz.

`wrap_user_message` kullanıcı girdisini yapısal sınırlar içine alır (veri/talimat ayrımı). Hızlı sorular ve model analizi özeti gibi **güvenilir** metinler doğrulamayı atlayan `sendMessage` yoludur.

## 4. İstem Politikası

- Danışman istemi (`ADVISOR_SYSTEM_PROMPT`): BIST uzmanı danışman rolü, araçları çağırma, spekülatif/kesin ifadelerden kaçınma, Türkçe sayı biçimi, kısa Markdown, her yanıtın sonunda özet/aksiyon ve "Yatırım tavsiyesi niteliğinde değildir." uyarısı.
- Genel sohbet istemi (`AiChatService.SYSTEM_PROMPT`): finans/piyasa/portföy dışı konulara ve yazılım yardımına yanıt vermez, yatırım tavsiyesi vermez, veride olmayan bilgi uydurmaz, açıklanabilirlik faktörlerini nedensellik kanıtı gibi anlatmaz, "Gündelik Özet" ile bitirir. Geçmişten en çok 20 mesaj gönderilir.
- LLM'e matematiksel hesap yaptırılmaz; sayılar yerel servislerden gelir, model yorumlar.

## 5. Hisse Modeli (AI_Core)

`ModelAnalysisController` (Yapay Zeka > Hisse Modeli): `probe()` ile AI_Core erişilebilirliğini yoklar, `analyze(ticker)` ile analiz üretir (arka planda). `AiAnalysisService` bağlantı varsa canlı sağlayıcıyı (`AICoreFastAPIClient`: `health_check`, `get_analysis`, `get_symbols`, `get_best_model`, `get_leaderboard`), yoksa `MockAIAnalysisProvider`'ı kullanır; analiz sırasında canlı sağlayıcı düşerse `mark_unavailable` ile demoya döner.

`AnalysisResult`: tahmin edilen fiyat, güven (0-1) ve gerekçe/uyarılar, yön beklentisi (`ModelOutlook`: yukarı/aşağı/nötr) ve gücü, son kapanış ve veri tazeliği, tahmin noktaları (aralık yöntemiyle), akran (peer) bilgisi (yüzdelik, etiket), trend olasılığı ve XAI faktörleri (en çok pozitif/negatif etkenler, yöntem uyarısı). **Demo sonuçlar gerçek değildir** ve arayüzde belirgin biçimde "demo" olarak işaretlenir. "Danışmana Gönder" analiz özetini sohbete aktarır (`sendToAdvisor`). AI_Core ayrı bir projedir (`ts_forecasting_lab`); bu depodaki istemci ve ayrıştırıcı hazırdır, servis kapalıysa demo çalışır.

## 6. Hata Yönetimi

Gemini/ağ hataları loga ayrıntılı yazılır; kullanıcıya kısa ve kibar Türkçe mesaj gösterilir. Anahtar yoksa danışman yerel motora düşer, karşılaştırma yorumu hata mesajı gösterir. Ağ çağrıları için genel yeniden deneme [service_market_data_providers.md](service_market_data_providers.md) içindedir (LLM çağrıları denenmez).

## 7. Testler

`tests/application/test_advisor_tools.py`, `test_ai_advisor_service.py`, `test_chat_session_service.py`, `tests/infrastructure/test_gemini_advisor_chat_provider.py` (sahte SDK; gerçek API'ye gidilmez), `tests/ui_qml/test_ai_advisor_phase10.py`, `test_model_analysis.py`. Gerçek Gemini ile uçtan uca doğrulama otomatik pakette yoktur (deterministik değil, ücretli).
