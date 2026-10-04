> Ana sayfa: [index.md](index.md) | Mimari: [architecture.md](architecture.md)

# Terimler Sözlüğü

Projede geçen alan ve teknik terimler. Ayrıntı için ilgili sayfaya bakın.

## Finans ve Piyasa

| Terim | Anlam |
|---|---|
| **BIST** | Borsa İstanbul. Seans: normal gün 10:00-18:10, yarım gün 10:00-13:00. |
| **Ticker** | Hisse kodu. Kanonik biçim uzantısız büyük harftir (`THYAO`); `.IS` yalnızca yfinance sınırında eklenir. |
| **Lot** | Hisse adedi birimi (portföyde `quantity`). |
| **Bedelsiz sermaye artırımı** | Ortaklara bedel ödemeden yeni pay verilmesi; lot artar, toplam maliyet sabit, ortalama maliyet ve fiyat düşer. |
| **Bedelli sermaye artırımı** | Ortakların kullanım fiyatı ödeyerek yeni pay alması; lot artar, toplam maliyete ödenen tutar eklenir. |
| **Ex-date** | Artırımın fiyata yansıdığı ilk gün; düzeltme bu günden önceki kayıtlara uygulanır. |
| **Teorik baz fiyat (TERP)** | Bedelli artırım sonrası beklenen fiyat. |
| **Temettü** | Nakit kâr payı. Bu projede net tutarla ve nakde giren getiri olarak kaydedilir. |
| **Golden / Death Cross** | EMA(50)'nin EMA(200)'ü yukarı (boğa) / aşağı (ayı) kesmesi. |
| **Seans / işlem günü** | BIST'in açık olduğu saat/gün; hafta sonu ve resmi tatiller işlem günü değildir. |
| **Carry-forward** | Fiyatı olmayan günde son bilinen fiyatın taşınması. |
| **Reel getiri** | TÜFE'den arındırılmış getiri. |
| **TÜFE (CPI)** | Tüketici fiyat endeksi (TCMB EVDS). |
| **EVDS** | TCMB Elektronik Veri Dağıtım Sistemi. |
| **KAP / MKK** | Kamuyu Aydınlatma Platformu / Merkezi Kayıt Kuruluşu; duyuru ve ortaklık yapısı kaynağı. |

## Risk ve Getiri

| Terim | Anlam |
|---|---|
| **TWR** | Zaman ağırlıklı getiri; dış sermaye akışlarından arındırılmış performans (başlangıç endeksi 100). |
| **Dış sermaye akışı** | Portföye yatırılan/çekilen para. Temettü akış değil getiridir. |
| **Sharpe oranı** | `(getiri - risksiz faiz) / volatilite`. |
| **Sortino, Calmar, Omega** | Sharpe benzeri risk ayarlı oranlar (aşağı yönlü risk, maksimum düşüş, kazanç/kayıp oranı). |
| **Drawdown (düşüş)** | Tarihsel zirveden yüzde düşüş; **maksimum drawdown** en derin düşüş. |
| **VaR / CVaR** | Belirli güven düzeyinde beklenen en kötü kayıp / eşik altındaki ortalama kayıp. |
| **Beta, Alpha** | Benchmark'a duyarlılık / benchmark'ın üstündeki getiri. |
| **Tracking error** | Portföy ile benchmark günlük getiri farkının yıllıklandırılmış standart sapması. |
| **Volatilite** | Getirilerin standart sapması; yıllık için `sqrt(252)` ile ölçeklenir. |
| **Markowitz / MPT** | Modern portföy teorisi; verimli sınır ve maksimum Sharpe ağırlıkları. |
| **Ledoit-Wolf** | Kovaryans matrisini büzüştürerek kararlı tahmin eden yöntem. |
| **Verimli sınır** | Her risk düzeyinde en yüksek getirili portföyler eğrisi. |
| **Rebalance** | Portföyü hedef ağırlığa döndürmek için alım/satım. |
| **DCA** | Düzenli periyodik alım (dollar-cost averaging). |
| **Al ve tut** | Başlangıç dağılımını hiç değiştirmeyen taban strateji. |
| **Stop-loss / take-profit** | Giriş fiyatına göre zarar durdurma / kâr alma eşiği. |
| **ADX, +DI, -DI** | Trend gücü ve yön göstergeleri (ADX > 25 güçlü trend). |
| **Supertrend** | ATR tabanlı trend takip çizgisi ve yönü. |
| **XAI** | Açıklanabilir yapay zekâ: modelin kararında etkili faktörler. |

## Mimari ve Veri

| Terim | Anlam |
|---|---|
| **Olay kaynaklı portföy** | Türev değerlerin saklanmayıp işlem geçmişinden yeniden hesaplanması ([service_portfolio_and_market.md](service_portfolio_and_market.md)). |
| **OLTP / OLAP** | İşlemsel (SQLite) / analitik (DuckDB) depo ([data_architecture.md](data_architecture.md)). |
| **Ham bar** | Düzeltilmemiş günlük OHLCV; DuckDB'de değişmez saklanır. |
| **Düzeltilmiş okuma** | Ham bar x (sonraki onaylı olayların faktör çarpımı) ([market_corporate_actions.md](market_corporate_actions.md)). |
| **Aday (candidate)** | Kullanıcı onayı bekleyen sermaye artırımı önerisi (KAP duyurusu veya veriden tespit). |
| **Faktör** | Fiyat düzeltme çarpanı (bedelsiz `1/(1+r)`). |
| **`daily_prices` / `latest_prices`** | Kapanış (tarihsel) / canlı fiyat tabloları ([service_portfolio_and_market.md](service_portfolio_and_market.md)). |
| **Scope (kapsam)** | Fiyat sağlığının taradığı portföy kümesi (tüm aktif, ana, model). |
| **Container (`AppContainer`)** | Bağımlılık enjeksiyonu facade'i ([architecture.md](architecture.md)). |
| **Port** | Domain'de tanımlı arayüz; altyapıda uygulanır. |
| **Denetleyici (controller)** | QML için Python `QObject` (ViewModel) ([ui_architecture_and_events.md](ui_architecture_and_events.md)). |
| **Context property** | `setContextProperty` ile QML'e açılan denetleyici. |
| **Lazy `Loader`** | Sayfanın ilk ziyarette yüklenmesi. |
| **EventBus** | `GlobalEventBus.prices_updated` Qt sinyali. |
| **Guard testi** | Mimari/standart kuralını otomatik denetleyen test ([testing_strategy.md](testing_strategy.md)). |
| **AI_Core** | Hisse tahmin/XAI üreten ayrı FastAPI projesi (`ts_forecasting_lab`). |
| **Tool-calling** | LLM'in tanımlı araçları çağırarak gerçek veriyle yanıt kurması ([ai_integration.md](ai_integration.md)). |
| **Retry / backoff** | Geçici ağ hatasında üstel bekleyerek yeniden deneme ([service_market_data_providers.md](service_market_data_providers.md)). |
