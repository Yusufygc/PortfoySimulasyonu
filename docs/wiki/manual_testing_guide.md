# Manuel Test Yönergesi

> Ana sayfa: [index.md](index.md) | Test stratejisi: [testing_strategy.md](testing_strategy.md) | Sayfa rehberi: [qml_pages_guide.md](qml_pages_guide.md)

Bu belge, QML arayüzünün 10 sayfasını ve kritik akışlarını yayın öncesi elle doğrulamak içindir. Otomatik testler denetleyici ve QML derlemesini kapsar ama gerçek pencere davranışını, WebEngine grafiklerini, dış servisleri ve çapraz sayfa etkilerini kapsamaz. Amaç yalnızca ekranların açılmasını değil; kalıcılığı, hata mesajlarını, geri dönüşleri ve sayfalar arası etkileri doğrulamaktır.

---

## 1. Test Kaydı Formatı

Her çalıştırmada: **ID**, **Durum** (Geçti / Kaldı / Engellendi / Uygulanamaz), **Ortam** (branch, commit, veritabanı, tarih-saat), **Kanıt** (ekran görüntüsü, log satırı, dosya), **Temizlik** (test verisi geri alındı mı).

```text
ID: DIV-002
Durum: Geçti
Ortam: qml / kopya_db / 2026-10-04 14:10
Kanıt: screenshots/temettu_listesi.png
Temizlik: Test temettüsü silindi.
```

---

## 2. Ortam Hazırlığı

### ENV-001 | Kopya veritabanı

- **Ön koşul:** Gerçek kişisel veri bozulmamalı.
- **Adımlar:**
  1. `data/portfolio.db` ve `data/market_history.duckdb` dosyalarını kopyala.
  2. `DB_SQLITE_PATH` ve `DUCKDB_PATH` ortam değişkenlerini kopyalara yönlendir ([development_guide.md](development_guide.md)).
  3. Branch/commit bilgisini ve başlangıç saatini not et.
- **Beklenen sonuç:** Tüm test kopya veride yapılır; gerçek dosyalar değişmez.

### ENV-002 | Uygulama başlatma

- **Adımlar:** `.\venv\Scripts\python.exe app.py`; `logs/app.log` dosyasını açık tut.
- **Beklenen sonuç:** Ana pencere açılır, "Genel Bakış" görünür, başlangıçta kritik exception loglanmaz. AI_Core çalışmıyorsa bağlantı reddi logu beklenir.

### ENV-003 | Minimum veri seti

- **Adımlar:** Ana portföye nakit yatır; en az üç hissede alım ve birinde kısmi satış gir (seans saatleri içinde, ör. 10:00-18:10 hafta içi); bir boş ve bir dolu izleme listesi; bir boş ve bir dolu model portföy; bir kayıtlı ve bir kayıtsız bütçe ayı, pinli kalem ve bir hedef; risk anketi doldurulmamış hâl.
- **Beklenen sonuç:** Tüm sayfalar boş, dolu ve hata durumlarıyla denenebilir.

---

## 3. Global Kontroller

### GLB-001 | Gezinme

- **Adımlar:** Kenar çubuğundan sırayla: Genel Bakış, İzleme Listeleri, Model Portföyler, Hisse 360, Karşılaştırma Lab, Hisse Tarayıcı, Finansal Planlama, Optimizasyon, AI Asistan, Ayarlar. Dar pencerede (<1100 px) kenar çubuğunun daraldığını ve içeriğin yatay/dikey kaydırıldığını doğrula.
- **Beklenen sonuç:** Donma, beyaz ekran veya yanlış aktif menü yok; sayfa ilk ziyarette yüklenir, sonra bellekte kalır.

### GLB-002 | Tema

- **Adımlar:** Ayarlar > Görünüm & Tema ile açık/koyu geçiş; tüm sayfaları gez; uygulamayı kapatıp aç.
- **Beklenen sonuç:** Metin, ikon, tablo, diyalog ve grafik okunur; seçim yeniden açılışta korunur.

### GLB-003 | Kalıcılık

- **Adımlar:** Bir işlem, izleme listesi, model portföy, bütçe ve ayar değişikliği yap; uygulamayı kapatıp aç.
- **Beklenen sonuç:** Veriler korunur.

### GLB-004 | Hata ve iptal

- **Adımlar:** Diyaloglarda İptal/kapatma; boş ad, sıfır/negatif tutar, geçersiz tarih dene; `logs/app.log`'u kontrol et.
- **Beklenen sonuç:** İptal veri yazmaz; geçersiz giriş açık Türkçe mesajla engellenir; uygulama kapanmaz.

### GLB-005 | Üst başlık

- **Adımlar:** Arama kutusuna `THYAO` yaz; piyasa şeridini ve senkron rozetini gözle.
- **Beklenen sonuç:** Arama Genel Bakış grafiğini ilgili hisseyle açar; şerit altın, gümüş, USD/TRY, EUR/TRY, BIST 100 gösterir (ağ yoksa ilgili öğeler gizlenir); senkron sürerken rozet görünür.

---

## 4. Genel Bakış (Dashboard)

### DASH-001 | KPI ve tablo

- **Beklenen sonuç:** Toplam değer, K/Z, günlük değişim, nakit, haftalık/aylık getiri ve "son güncelleme" görünür; pozisyon tablosu lot, maliyet, güncel fiyat, günlük %, ağırlık gösterir; tutarlar Türkçe biçimlidir; varlık dağılımı donut'u pozisyonlarla uyumludur.

### DASH-002 | Alım

- **Adımlar:** Hızlı işlem: hisse kodu, lot, fiyat, tarih ve saat gir.
- **Beklenen sonuç:** Yeterli nakit varsa kayıt oluşur ve tablo/KPI yenilenir; yetersiz nakit, seans dışı saat, hafta sonu/tatil ve geçersiz kod açık mesajla reddedilir.

### DASH-003 | Satış

- **Adımlar:** Eldeki lottan fazla satış dene; geçmiş tarihli satış dene.
- **Beklenen sonuç:** Fazla satış ve sonraki akışı bozan geçmiş tarihli kayıt reddedilir.

### DASH-004 | Sermaye

- **Adımlar:** Yatır ve çek; bakiyeden fazla çekmeyi dene.
- **Beklenen sonuç:** Bakiye güncellenir; fazla çekim reddedilir. Sermaye hareketleri seans kuralına tabi değildir.

### DASH-005 | Otomatik fiyat güncelleme

- **Adımlar:** (a) Uygulamayı BIST seansı içinde açın ve bekleyin. (b) Uygulamayı 18:30'dan sonra (veya gece/hafta sonu) açın ve bekleyin. (c) Başlık altındaki küçük yenile ikonuna tıklayın.
- **Beklenen sonuç:** Düğmeye basmadan Ana Sayfa, İzleme Listesi ve Model Portföy aynı fiyatı gösterir. (a) Canlı fiyat gelir, "Son güncelleme" ilerler. (b) Bugünün kapanışı gelir; günlük değişim son iki kapanıştan hesaplanır (%0 değil). (c) Seans içinde canlı, dışında kapanış senkronu çalışır; ikon dönerken arayüz donmaz.

### DASH-006 | Grafik

- **Adımlar:** Zaman dilimi (1D/1W/1M), grafik tipi, göstergeler (SMA/EMA, Bollinger, RSI, MACD), tam ekran.
- **Beklenen sonuç:** Grafik tüm seçimlerde yeniden çizilir; boş veride açıklayıcı durum gösterilir.

### DASH-007 | Excel raporu

- **Adımlar:** Excel Raporu: tarih aralığı, dosya, "ekle" modu açık/kapalı.
- **Beklenen sonuç:** Dört sayfalı dosya oluşur (Özet Panel, Portföy Özeti, Günlük Detaylar, Hisse Özeti); ekleme modunda tarihler tekrarlanmaz; geçersiz tarih mesajla reddedilir.

---

## 5. Hisse Detay Modalı

### SD-001 | Açılış ve içerik

- **Adımlar:** Pozisyon satırına tıkla.
- **Beklenen sonuç:** Lot, ortalama maliyet, piyasa değeri, K/Z; "İşlem Geçmişi" ve "Sermaye Artırımları" sekmeleri; hızlı emir formu işlem etkisini (yeni lot, ortalama maliyet, kalan nakit) canlı gösterir.

### SD-002 | Sermaye artırımı

- **Adımlar:** Bedelsiz (ör. %50) gir; ön izlemeyi incele; uygula. Ardından aynı aksiyonu tekrar dene.
- **Beklenen sonuç:** Yeni lot aşağı yuvarlanır, ortalama maliyet düşer, geçmiş işlemler ve fiyat grafiği ex-date öncesi düzeltilir; tekrar uygulama reddedilir; Dashboard yenilenir. Bedelli için kullanım fiyatı zorunludur.

### SD-003 | Temettü (DIV)

- **Adımlar:** Temettü: net tutar (`1.250,50`), tarih, not; ekle. Pozisyon öncesi tarih ve gelecek tarih dene. Kaydı sil.
- **Beklenen sonuç:** Tutar nakit bakiyeye eklenir ve listede görünür; pozisyon yokken ve gelecek tarihte reddedilir; temettü sermaye girişi sayılmaz (getiri grafiğinde getiri olarak görünür); sonraki alımı finanse ettiyse silme reddedilir.

### SD-004 | Diğer

- **Adımlar:** TradingView grafiği, Hisse 360'a geçiş, hisse Excel'i; model portföy bağlamında aç.
- **Beklenen sonuç:** Geçişler doğru hisseyi açar; Excel oluşur; model bağlamında Sermaye Artırımı ve Temettü düğmeleri görünmez.

---

## 6. İzleme Listeleri

### WL-001 | Liste yönetimi

- **Adımlar:** Liste oluştur, düzenle, sil, sürükle-bırak sırala.
- **Beklenen sonuç:** Sıralama ve içerik yeniden açılışta korunur.

### WL-002 | Hisse ekleme

- **Adımlar:** Bilinen kod (`THYAO`), `.IS` uzantılı kod, bilinmeyen geçerli kod, geçersiz kod ekle.
- **Beklenen sonuç:** Bilinen kodlar doğrudan eklenir (uzantı temizlenir); geçersiz kod "Geçersiz hisse kodu" ile reddedilir ve kayıt oluşmaz.

### WL-003 | Tablo

- **Beklenen sonuç:** Fiyat, günlük değişim, sparkline ve not görünür; not düzenlenir; satırdan hızlı işlem açılır; boş liste boş durum gösterir.

---

## 7. Model Portföyler

### MP-001 | CRUD ve sıralama

- **Beklenen sonuç:** Oluşturma (başlangıç sermayesi), düzenleme, silme ve sürükle-bırak sıralama çalışır; ilk portföy otomatik seçilir; liste boşsa sağ panel temizlenir.

### MP-002 | İşlem ve sermaye

- **Adımlar:** Hisse al/sat, sermaye yatır/çek, geçmiş tarihli hareket.
- **Beklenen sonuç:** Nakit kontrolü ve zaman çizelgesi doğrulaması çalışır; K/Z = toplam değer - net sermaye (sermaye eklemek kâr sayılmaz); seans koruması alım/satımda uygulanır.

### MP-003 | Fiyat ve rapor

- **Adımlar:** Fiyat güncellemesini bekleyin (veya küçük yenile ikonu); Excel raporu.
- **Beklenen sonuç:** Seçili portföy düğmesiz yeni fiyatı gösterir; canlı fiyat `daily_prices` yazmaz; rapor öncesi eksik kapanış varsa uyarı listesi çıkar.

---

## 8. Hisse 360

### S360-001 | Arama ve genel bakış

- **Adımlar:** `THYAO`, portföyde olmayan bir BIST hissesi, `.IS` uzantılı kod, geçersiz kod ara.
- **Beklenen sonuç:** Fiyat, günlük değişim, 52 hafta aralığı, hacim ve teknik seviyeler anında gelir; portföy dışı hisselerde de çalışır; geçersiz kod hata gösterir.

### S360-002 | Finansal tablolar

- **Adımlar:** Sekme, tablo türü (bilanço, gelir, nakit akımı), dönem (4/8/12/tüm çeyrek), arama.
- **Beklenen sonuç:** Veri arka planda yüklenir (yükleniyor göstergesi); rasyolar, DuPont, nakit akışı ve gelir grafiği dolar; ağ yoksa yedek veri/hata mesajı görünür, sayfa çökmez.

### S360-003 | Ortaklık yapısı

- **Beklenen sonuç:** KAP pay sahipleri pasta ve zaman çizelgesiyle gelir; yenileme çalışır; erişilemezse bölüm hata gösterir.

---

## 9. Karşılaştırma Lab

### CMP-001 | Seçim ve dönem

- **Adımlar:** Ana Portföy, bir model portföy, "Portföy + Hisseleri", BIST 100, altın, USD/TRY, TÜFE seç; dönemleri (1A, 3A, 6A, 1Y, YBB, Tümü, ÖZEL) dene.
- **Beklenen sonuç:** Her değişiklikte hesap yeniden çalışır; ÖZEL aralıkta geçersiz tarih reddedilir; ortak 2 gün yoksa boş durum gösterilir.

### CMP-002 | Modlar ve para birimi

- **Adımlar:** Normal, Normalize (Baz 100), Rasyo (A/B); TL, USD, Reel (TÜFE).
- **Beklenen sonuç:** Eğriler moda ve para birimine göre değişir; rasyo için pay ve payda seçimi zorunludur.

### CMP-003 | Grafik sekmeleri

- **Adımlar:** Kümülatif, Drawdown, Aylık Getiriler, Risk-Getiri Saçılımı, Treemap (Portföy Hisseleri / Varlık Kıyaslaması).
- **Beklenen sonuç:** Her sekme çizilir; risk-getiri tablosu toplam getiri ve volatiliteyi gösterir; bilgi kartları (Nedir / Nasıl Yorumlanır) açılır-kapanır.

### CMP-004 | Yapay zeka yorumu

- **Adımlar:** "Yapay Zeka Yorumu" (anahtar var/yok).
- **Beklenen sonuç:** Anahtar varsa yorum üretilir ve yenilenebilir; yoksa açık hata mesajı; "yatırım tavsiyesi değildir" uyarısı görünür.

---

## 10. Hisse Tarayıcı

### SCR-001 | Strateji taraması

- **Adımlar:** "Tüm Stratejiler" ve tek tek (ADX, Supertrend dahil) tara.
- **Beklenen sonuç:** Birkaç saniyede sonuç gelir; liste hisse, strateji ve son fiyat gösterir; çift tıklama grafiği, tek tıklama Hisse 360'ı açar; sonuç yoksa boş durum mesajı çıkar.

### SCR-002 | Golden Cross

- **Adımlar:** Gün sayısı ve tür (Golden/Death) filtresi; tek hisse geçmişi; "Tümünü tara"; "veriyi tamamla".
- **Beklenen sonuç:** Liste filtreye göre güncellenir; tarama arka planda çalışır ve ekran donmaz.

---

## 11. Finansal Planlama

### FP-BUD-001 | Bütçe

- **Adımlar:** Ay seç; gelir/gider ekle, düzenle, sil; tasarruf hedefi; kalemi pinle; kayıtsız aya geç.
- **Beklenen sonuç:** Toplam gelir/gider/net ve durum mesajı doğrudur; pinli kalemler yalnızca bütçesi olmayan ayda taslak olarak gelir; kayıtlı aylar değişmez.

### FP-GOAL-001 | Hedefler

- **Adımlar:** Hedef ekle, düzenle, sil, katkı ekle; öncelik değiştir.
- **Beklenen sonuç:** İlerleme çubuğu ve fizibilite durumu (BAŞARILI/YETERSİZ KAYNAK/KRİTİK/BİLGİ) doğru görünür.

### FP-DCA-001 | DCA

- **Adımlar:** Hisseler (`THYAO FROTO`), aylık tutar, başlangıç/bitiş tarihi, çalıştır.
- **Beklenen sonuç:** Değer eğrisi, toplam yatırılan, nihai değer, getiri ve katkı sayısı gelir; geçersiz hisse atlanır.

### FP-STR-001 | Strateji Testi

- **Adımlar:** Yeniden dengeleme (3 aylık, eşit; sonra Markowitz); stop-loss/take-profit (örn. %10/%30); komisyon %0,1; hata girdileri (tek hisse, negatif sermaye, eşiksiz stop-take, gelecek tarih).
- **Beklenen sonuç:** KPI (strateji ve al-tut getirisi, fark, maksimum düşüş), özet satırı (dönem, dengeleme/çıkış sayısı), çift çizgili grafik ve olay listesi gelir; Markowitz veri yetersizse "Uyarı" olayı görünür; hatalı girdi açık mesajla reddedilir; `50.000` sermaye 50 bin olarak okunur.

---

## 12. Optimizasyon ve Risk Profili

### OPT-001 | Kaynak ve çalıştırma

- **Adımlar:** Ana portföy ve model portföy seç; risk profili, tek hisse üst sınırı, risksiz faiz ayarla; optimize et.
- **Beklenen sonuç:** KPI kartları (maksimum Sharpe, getiri, risk, minimum volatilite) gelir; Verimli Sınır, Ağırlık Dağılımı ve Yeniden Dengeleme sekmeleri dolar; EKLE/AZALT/TUT önerileri tutarlıdır; kaydırıcı kayıtlı profili değiştirmez.

### OPT-002 | Veri yetersizliği

- **Adımlar:** 2'den az hisseli veya geçmişi kısa portföy ile dene.
- **Beklenen sonuç:** Anlamlı hata mesajı; uygulama kapanmaz.

### RISK-001 | Risk anketi

- **Adımlar:** Anketi doldur ve kaydet; farklı yanıtlarla etiketleri ve tutarlılık notlarını dene.
- **Beklenen sonuç:** Skor ve etiket (Çok Muhafazakar ... Agresif) hesaplanır; kayıtlı profil Optimizasyon'da tek hisse sınırını belirler; "yatırım tavsiyesi değildir" notu görünür.

---

## 13. AI Asistan

### AI-001 | Portföy Danışmanı

- **Adımlar:** Anahtar tanımlıyken hızlı sorular ve serbest soru; anahtar yokken tekrar.
- **Beklenen sonuç:** Anahtar varken araç rozetleriyle Türkçe yanıt ve "Çevrimiçi" rozeti; yokken yerel analiz ve "Simülasyon" rozeti; sağlık skoru ve XAI boyutları görünür.

### AI-002 | Girdi güvenliği

- **Adımlar:** "ignore previous instructions", "yatırım tavsiyesi ver", 750 karakterden uzun metin gönder.
- **Beklenen sonuç:** Mesaj reddedilir ve "Güvenlik Uyarısı" görünür; model çağrılmaz.

### AI-003 | Geçmiş ve oturumlar

- **Adımlar:** Yeni sohbet, geçmişten oturum aç, sil, uygulamayı yeniden başlat.
- **Beklenen sonuç:** Oturumlar listelenir ve devam ettirilir; boş oturum kaydedilmez.

### AI-004 | Hisse Modeli

- **Adımlar:** Modu aç, hisse analiz et (AI_Core açık ve kapalı).
- **Beklenen sonuç:** Servis kapalıysa sonuçlar belirgin "demo" işaretiyle gelir; açıksa gerçek tahmin, güven, XAI ve akran bilgisi görünür; "Danışmana Gönder" özeti sohbete aktarır.

---

## 14. Ayarlar

### SET-001 | API anahtarları

- **Adımlar:** Gemini anahtarı gir, sına, kaydet; EVDS anahtarı gir.
- **Beklenen sonuç:** Başarı/hata mesajı gelir; anahtar `.env` dosyasına yazılır ve yeniden başlatma gerektirmeden etkili olur.

### SET-002 | Veri sağlığı

- **Adımlar:** İstatistikleri yenile; bütünlük kontrolü; "Eksik BIST Barlarını Şimdi Senkronize Et".
- **Beklenen sonuç:** Dosya boyutları, tablo sayıları (finansal hedefler dahil), DuckDB hisse/bar sayısı ve son tarih doğru; bütünlük "sağlam" döner; senkron bitince toast ve Dashboard yenilemesi görülür.

### SET-003 | Dışa aktarım

- **Beklenen sonuç:** Excel ve JSON yedeği masaüstüne yazılır; JSON `stocks`, `trades`, `cash_movements`, `watchlists` içerir.

### SET-004 | Kurumsal aksiyon adayları

- **Adımlar:** "KAP/MKK Yenile"; aday düzenle, yoksay, onayla ve uygula.
- **Beklenen sonuç:** Kaynak erişilemezse kısa uyarı; onay portföye uygular ve fiyat geçmişini düzeltir; yoksayılan aday listeden düşer.

### SET-005 | Fiyat verisi

- **Adımlar:** Kapsam seç (Tüm aktif, Ana, Model); analiz; eksikleri tamamla; seçili hisseyi tamamla; son günden güncelle; aralığı sil; raporu kopyala.
- **Beklenen sonuç:** Eksik gün sayıları ve tatil adayları doğru; güncelleme son tamamlanmış işlem gününe kadardır.

### SET-006 | Piyasa düzeltmeleri

- **Adımlar:** Durum/ticker/yıl filtresi; "Tara"; aday onayla (faktör düzenle), yoksay, yeniden aç.
- **Beklenen sonuç:** Onaylanan olay tarayıcı ve grafiklerde düzeltilmiş fiyatı etkiler; yoksayılan etkilemez; liste olay sayacını gösterir.

### SET-007 | Sistem

- **Adımlar:** Canlı yenilemeyi aç/kapat, aralık değiştir, "Şimdi Yenile"; (yalnızca kopya veride) "Sistemi Sıfırla".
- **Beklenen sonuç:** Ayarlar yeniden açılışta korunur; yenileme yalnızca seans açıkken çalışır; sıfırlama onay ister ve portföy, işlem, nakit, izleme listesi, model portföy ve hisseleri siler (DuckDB ve bütçe silinmez).

---

## 15. Arka Plan Davranışı

### BG-001 | Açılış işleri

- **Adımlar:** Uygulamayı aç ve 10-15 sn bekle; `logs/app.log` ve toast'lara bak.
- **Beklenen sonuç:** Catch-up senkronu (5 sn), canlı yenileme (6 sn) ve açılış bakım işleri (8 sn) hata vermeden başlar; yeni fiyat/aday/sinyal varsa toast gösterilir; gün içinde tekrar açınca tamamlanmış işler atlanır.

### BG-002 | Ağ yokken

- **Adımlar:** Ağı kes, uygulamayı aç.
- **Beklenen sonuç:** Yerel veri (Dashboard, Hisse 360 genel bakış, tarayıcı) çalışır; dış veriye bağlı bölümler kısa hata mesajı verir; sayfa donmaz.
