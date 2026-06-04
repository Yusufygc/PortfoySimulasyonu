# Kapsamlı Manuel Test Yönergesi

> Ana sayfa: [index.md](index.md) | Değişiklik günlüğü: [log.md](log.md) | Test stratejisi: [testing_strategy.md](testing_strategy.md)

Bu belge, Portföy Simülasyonu masaüstü uygulamasının her ana sayfasını ve kritik kullanıcı akışlarını manuel olarak test etmek için hazırlanmıştır. Amaç, yeni sürüm öncesinde yalnızca ekranların açıldığını değil, veri kalıcılığı, hata mesajları, uyarılar, geri dönüşler, dış servis bağımlılıkları ve çapraz sayfa etkilerini de doğrulamaktır.

---

## 1. Test Kaydı Formatı

Her manuel test çalıştırmasında aşağıdaki format kullanılmalıdır:

- **ID:** Rehberdeki test kimliği.
- **Durum:** Geçti / Kaldı / Engellendi / Uygulanamaz.
- **Ortam:** Branch, commit, veritabanı adı, Python ortamı, tarih-saat.
- **Kanıt:** Ekran görüntüsü, log satırı, export dosyası, hata mesajı veya kısa not.
- **Temizlik:** Testin bıraktığı veri geri alındı mı, yedekten dönüldü mü, yoksa veri bilinçli olarak korundu mu.

Önerilen kayıt örneği:

```text
ID: FP-BUD-006
Durum: Geçti
Ortam: local / test_db / 2026-06-04 21:30
Kanıt: screenshots/fp_budget_pin_empty_month.png
Temizlik: Test ayı ve pinli kalemler test sonunda silindi.
```

---

## 2. Ortam Hazırlığı

### ENV-001 | Test veritabanı ve yedek

- **Ön koşul:** Testler canlı/verimli kişisel veriyi bozmayacak ayrı bir DB üzerinde yapılmalı.
- **Adımlar:**
  1. `.env` dosyasındaki `DB_NAME` değerinin test veritabanını gösterdiğini doğrula.
  2. Yıkıcı testlerden önce DB yedeği al.
  3. Test başlangıç saatini ve branch/commit bilgisini kaydet.
- **Beklenen sonuç:** Test verisi geri alınabilir durumdadır; canlı veri üzerinde reset/silme yapılmaz.
- **Kanıt:** DB adı, yedek dosya adı veya kısa ortam notu.

### ENV-002 | Uygulama başlatma

- **Ön koşul:** Bağımlılıklar kurulu, `.env` geçerli.
- **Adımlar:**
  1. Proje kökünde terminal aç.
  2. Gerekli Python ortamını aktive et.
  3. `python app.py` komutuyla uygulamayı başlat.
  4. `logs/app.log` dosyasını açık tut.
- **Beklenen sonuç:** Ana pencere açılır, uygulama kilitlenmez, başlangıçta kritik exception loglanmaz.
- **Kanıt:** Ana ekran görüntüsü ve son log satırları.

### ENV-003 | Minimum test veri seti

- **Ön koşul:** Uygulama açık.
- **Adımlar:**
  1. Ana portföyde nakit bakiyesi oluştur.
  2. En az üç hissede alış işlemi gir.
  3. En az bir hissede kısmi veya tam satış işlemi gir.
  4. Bir boş ve bir dolu izleme listesi oluştur.
  5. Bir boş ve bir dolu model portföy oluştur.
  6. Finansal Planlama için bir kayıtlı bütçe ayı, bir kayıtsız ay, pinli gelir/gider ve bir finansal hedef oluştur.
  7. Risk profili için hem profil yok hem profil var durumunu test edecek not al.
  8. Ayarlar > Fiyat Verisi Yönetimi için fiyat eksiği bulunan en az bir hisse belirle.
  9. Kurumsal aksiyon testleri için yalnızca test DB'de kullanılacak bir aday veya manuel senaryo hazırla.
- **Beklenen sonuç:** Tüm ana ekranlar boş, dolu ve hata durumlarıyla test edilebilir.
- **Kanıt:** Test veri matrisi notu.

---

## 3. Global Kontroller

### GLB-001 | Navigasyon ve sayfa yaşam döngüsü

- **Adımlar:**
  1. Sol menüdeki tüm sayfalara sırayla git: Ana Sayfa, Listelerim, Model Portföyler, Analiz, Karşılaştırma, Optimizasyon, Finansal Planlama, Risk Profili, AI Asistan, Ayarlar.
  2. Her geçişte seçili menü durumunu ve sayfanın veri yüklediğini kontrol et.
  3. Aynı sayfaya ikinci kez dönüp verinin yeniden yüklenip yüklenmediğini gözle.
- **Beklenen sonuç:** Sayfa geçişlerinde donma, boş beyaz ekran, stale veri veya yanlış aktif menü yoktur.
- **Kanıt:** Kısa video veya her sayfadan ekran görüntüsü.

### GLB-002 | Tema ve görsel tutarlılık

- **Adımlar:**
  1. Ayarlar > Görünüm üzerinden açık ve koyu tema arasında geçiş yap.
  2. Tüm ana sayfalara dön.
  3. Tablo, buton, kart, dialog ve grafiklerin okunabilirliğini kontrol et.
- **Beklenen sonuç:** Tema değişimi uygulama genelinde uygulanır; metinler görünür, ikonlar kaybolmaz, inline bozuk stil oluşmaz.
- **Kanıt:** Açık/koyu tema ekran görüntüleri.

### GLB-003 | Veri kalıcılığı

- **Adımlar:**
  1. Bir işlem, bir watchlist, bir model portföy, bir bütçe ve bir ayar değişikliği yap.
  2. Uygulamayı kapatıp yeniden aç.
  3. Aynı sayfalarda verilerin korunup korunmadığını kontrol et.
- **Beklenen sonuç:** Kalıcı olması gereken veriler korunur; geçici hesaplamalar doğru şekilde yeniden üretilir.
- **Kanıt:** Önce/sonra ekran görüntüleri.

### GLB-004 | Hata ve iptal davranışı

- **Adımlar:**
  1. Kritik dialoglarda İptal veya pencere kapatma aksiyonunu dene.
  2. Geçersiz girişleri dene: boş isim, sıfır tutar, negatif tutar, geçersiz tarih aralığı.
  3. Log dosyasında kritik exception olup olmadığını kontrol et.
- **Beklenen sonuç:** Kullanıcı iptali veri yazmaz; geçersiz girişler açık mesajla engellenir; uygulama kapanmaz.
- **Kanıt:** Uyarı mesajı görüntüsü ve log notu.

---

## 4. Ana Sayfa / Dashboard

### DASH-001 | Portföy özet kartları

- **Ön koşul:** En az bir açık pozisyon ve nakit bakiyesi var.
- **Adımlar:**
  1. Ana Sayfa'yı aç.
  2. Toplam değer, maliyet, nakit, kar/zarar ve getiri kartlarını kontrol et.
  3. Fiyat güncellemesi sonrası kartları tekrar kontrol et.
- **Beklenen sonuç:** Kartlar boş veya hatalı formatta değildir; nakit negatif gösterilmez; fiyat değişimi ilgili değerleri günceller.
- **Kanıt:** Fiyat güncelleme öncesi/sonrası ekran görüntüsü.

### DASH-002 | Portföy tablosu ve hisse detayına geçiş

- **Adımlar:**
  1. Portföy tablosunda her satırda ticker, adet, maliyet, güncel fiyat ve kar/zarar alanlarını kontrol et.
  2. Bir satıra çift tıkla.
  3. Hisse Detayı sayfasının doğru hisseyle açıldığını doğrula.
  4. Geri butonuyla Dashboard'a dön.
- **Beklenen sonuç:** Çift tıklanan ticker detay sayfasında aynıdır; geri dönüş önceki sayfayı bozmadan çalışır.
- **Kanıt:** Ticker eşleşmesini gösteren ekran görüntüsü.

### DASH-003 | Yeni işlem sihirbazı - alış

- **Adımlar:**
  1. `Yeni İşlem` butonuna bas.
  2. Geçerli bir ticker ara ve lookup sonucunu bekle.
  3. Alış seç, adet ve tarih/saat gir.
  4. Tutar ve fiyat bilgisinin doğru hesaplandığını kontrol et.
  5. İşlemi kaydet.
- **Beklenen sonuç:** Yeni alış portföy tablosuna yansır, nakit azalır, logda kritik hata yoktur.
- **Kanıt:** İşlem öncesi/sonrası portföy satırı.

### DASH-004 | Yeni işlem sihirbazı - satış ve validasyon

- **Adımlar:**
  1. Mevcut pozisyonu olan bir hisse için satış gir.
  2. Önce eldeki miktardan fazla satış dene.
  3. Sonra geçerli satış miktarıyla kaydet.
- **Beklenen sonuç:** Fazla satış engellenir; geçerli satış pozisyonu ve nakdi günceller.
- **Kanıt:** Uyarı mesajı ve başarılı satış sonrası tablo.

### DASH-005 | Piyasa/fiyat uyarıları

- **Adımlar:**
  1. Fiyatı bulunamayan veya piyasa saati dışında işlem senaryosunu dene.
  2. Uygulamanın onay/uyarı penceresini gösterdiğini kontrol et.
  3. İptal ve devam seçeneklerini ayrı ayrı test et.
- **Beklenen sonuç:** İptal veri yazmaz; devam seçilirse beklenen işlem akışı sürer.
- **Kanıt:** Onay penceresi görüntüsü.

### DASH-006 | Sermaye yönetimi

- **Adımlar:**
  1. `Sermaye Yönetimi` dialogunu aç.
  2. Para yatırma işlemi gir.
  3. Para çekme işlemi gir.
  4. Bakiyeden fazla çekim dene.
- **Beklenen sonuç:** Yatırma nakdi artırır; çekme nakdi azaltır; yetersiz nakit engellenir.
- **Kanıt:** Nakit kartı önce/sonra.

### DASH-007 | Fiyatları güncelle

- **Adımlar:**
  1. `Fiyatları Güncelle` butonuna bas.
  2. Loading/disabled durumunu gözle.
  3. İşlem bitince tablo ve özet kartların güncellendiğini kontrol et.
- **Beklenen sonuç:** UI donmaz; sonuç kullanıcıya bildirilir; fiyat event'i ilgili ekranlara yansır.
- **Kanıt:** Güncelleme sonrası toast/status.

### DASH-008 | Rapor alma

- **Adımlar:**
  1. `Rapor Al > Bugün` seç.
  2. Oluşan dosyayı açılabilirlik açısından kontrol et.
  3. `Rapor Al > Tarih Aralığı` seç ve geçerli aralık gir.
  4. Başlangıç > bitiş gibi geçersiz aralık dene.
- **Beklenen sonuç:** Geçerli rapor üretilir; geçersiz tarih engellenir.
- **Kanıt:** Export dosya adı ve uyarı ekranı.

### DASH-009 | Kurumsal aksiyon uygulama

- **Ön koşul:** Test DB veya yedek alınmış DB.
- **Adımlar:**
  1. Uygun portföy satırından kurumsal aksiyon dialogunu aç.
  2. Bedelli/bedelsiz senaryosunu uygula.
  3. Pozisyon adet/maliyet ve geçmiş fiyat etkisini kontrol et.
- **Beklenen sonuç:** İşlem idempotent ve açıklanabilir sonuç üretir; iptal veri yazmaz.
- **Kanıt:** Uygulama öncesi/sonrası pozisyon verisi.

---

## 5. Listelerim

### WLIST-001 | Liste oluşturma

- **Adımlar:**
  1. Listelerim sayfasını aç.
  2. Yeni liste oluştur.
  3. Boş isim ve tekrar eden isim dene.
- **Beklenen sonuç:** Geçerli liste kaydedilir; geçersiz isimler engellenir veya açık mesaj verir.
- **Kanıt:** Sol liste paneli görüntüsü.

### WLIST-002 | Liste düzenleme, silme ve sıralama

- **Adımlar:**
  1. Var olan listeyi yeniden adlandır.
  2. Liste satırındaki silme aksiyonunu kullan.
  3. Onay penceresinde iptal ve onay davranışlarını test et.
  4. Listeleri sürükle-bırak ile yeniden sırala.
- **Beklenen sonuç:** İptal veri silmez; onay siler; sıra yeniden açılışta korunur.
- **Kanıt:** Sıralama önce/sonra.

### WLIST-003 | Listeye hisse ekleme ve çıkarma

- **Adımlar:**
  1. Dolu olmayan bir liste seç.
  2. `Hisse Ekle` akışını aç.
  3. Geçerli ticker ekle.
  4. Aynı hisseyi tekrar eklemeyi dene.
  5. Hisseyi listeden çıkar.
- **Beklenen sonuç:** Geçerli hisse görünür; duplicate engellenir; çıkarma sonrası tablo güncellenir.
- **Kanıt:** Liste içeriği ekranı.

### WLIST-004 | Boş durum

- **Adımlar:**
  1. Boş bir watchlist seç veya tüm hisseleri çıkar.
  2. Boş durum metni ve aksiyon butonunu kontrol et.
  3. Boş durumdan hisse ekle.
- **Beklenen sonuç:** Kullanıcı boş ekranda kilitlenmez; ekleme sonrası normal tabloya döner.
- **Kanıt:** Boş durum ve dolu durum görüntüleri.

---

## 6. Model Portföyler

### MP-001 | Model portföy oluşturma ve seçim

- **Adımlar:**
  1. Yeni model portföy oluştur.
  2. Liste panelinde seçili duruma geçtiğini kontrol et.
  3. Uygulamayı yeniden açıp son/geçerli seçimin korunup korunmadığını kontrol et.
- **Beklenen sonuç:** Portföy oluşturulur, sağ panel doğru portföyü gösterir, geçersiz eski seçim varsa uygulama ilk geçerli portföye döner.
- **Kanıt:** Liste ve başlık eşleşmesi.

### MP-002 | Düzenleme, silme ve sıralama

- **Adımlar:**
  1. Portföy adını düzenle.
  2. Portföyleri sürükle-bırak ile sırala.
  3. Boş ve dolu portföy silme akışını dene.
- **Beklenen sonuç:** Onay akışı çalışır; silinen portföy sağ panelde stale veri bırakmaz.
- **Kanıt:** Önce/sonra liste paneli.

### MP-003 | Model portföyde hisse al

- **Adımlar:**
  1. Dolu veya boş model portföy seç.
  2. `Hisse Al` dialogunu aç.
  3. Geçerli ticker, lot, fiyat ve tarih gir.
  4. Tutar alanının `Lot x Fiyat` olarak güncellendiğini doğrula.
  5. Kaydet.
- **Beklenen sonuç:** Pozisyon tabloya eklenir; sermaye/nakit etkisi doğru gösterilir.
- **Kanıt:** Pozisyon tablosu.

### MP-004 | Model portföyde hisse sat

- **Adımlar:**
  1. Pozisyonsuz portföyde `Hisse Sat` butonunun pasif olduğunu kontrol et.
  2. Pozisyonlu portföyde satış dialogunu aç.
  3. Elde olmayan miktar ve geçerli miktar senaryolarını dene.
- **Beklenen sonuç:** Pozisyonsuz satış engellenir; fazla satış hata verir; geçerli satış tabloya yansır.
- **Kanıt:** Buton durumu ve satış sonrası tablo.

### MP-005 | Sermaye yönetimi

- **Adımlar:**
  1. `Sermaye Yönetimi` dialogunu aç.
  2. Sermaye ekle ve çıkar.
  3. Aynı tarih/saatte trade ile sermaye hareketi etkisini gözlemle.
- **Beklenen sonuç:** Net kar/zarar sermaye ekleme/çekmeden yapay etkilenmez; nakit doğru hesaplanır.
- **Kanıt:** Özet kartları.

### MP-006 | Fiyat yenileme ve rapor

- **Adımlar:**
  1. `Fiyat Güncelle` butonuna bas.
  2. Pozisyon fiyatlarının güncellendiğini kontrol et.
  3. `Rapor Al` menüsünden bugün ve tarih aralığı raporu üret.
- **Beklenen sonuç:** Fiyatlar memory/event akışıyla güncellenir; rapor dosyaları açılabilir.
- **Kanıt:** Toast/status ve dosya.

### MP-007 | Hisse detayına geçiş

- **Adımlar:**
  1. Model portföy pozisyon satırına çift tıkla.
  2. Hisse Detayı'nın model portföy bağlamıyla açıldığını kontrol et.
  3. Geri dön.
- **Beklenen sonuç:** Detay sayfası doğru ticker ve model portföy verisiyle açılır.
- **Kanıt:** Detay başlığı.

---

## 7. Hisse Detayı

### SD-001 | Dashboard bağlamından detay

- **Adımlar:**
  1. Dashboard tablosundan bir hisseye çift tıkla.
  2. Fiyat, grafik, istatistik ve işlem geçmişini kontrol et.
  3. Geri butonunu kullan.
- **Beklenen sonuç:** Detay sayfası ana portföy bağlamında doğru veriyi gösterir; geri dönüş Dashboard'a döner.
- **Kanıt:** Ticker ve işlem geçmişi ekranı.

### SD-002 | Model portföy bağlamından detay

- **Adımlar:**
  1. Model Portföyler sayfasından bir pozisyona çift tıkla.
  2. Detay sayfasında model portföy bağlamının korunduğunu kontrol et.
  3. Geri butonuyla Model Portföyler'e dön.
- **Beklenen sonuç:** Ana portföy ile model portföy verisi karışmaz.
- **Kanıt:** Başlık ve geri dönüş ekranı.

### SD-003 | Hızlı işlem formu

- **Adımlar:**
  1. Alış modunu seç, lot gir, etki önizlemesini kontrol et.
  2. Satış modunu seç, geçersiz ve geçerli lot dene.
  3. Tarih/saat alanlarını değiştir.
  4. İşlemi onayla.
- **Beklenen sonuç:** Önizleme canlı güncellenir; geçersiz işlem engellenir; geçerli işlem ilgili portföye yazılır.
- **Kanıt:** İşlem sonrası detay ve kaynak sayfa.

### SD-004 | Fiyat/grafik yokluğu

- **Adımlar:**
  1. Fiyat geçmişi eksik olan bir hisse aç.
  2. Grafik ve metrik alanlarının boş veri davranışını kontrol et.
- **Beklenen sonuç:** Sayfa çökmez; kullanıcıya anlaşılır boş/veri yok durumu gösterilir.
- **Kanıt:** Boş veri ekranı.

---

## 8. Analiz

### ANL-001 | İlk yükleme ve sekmeler

- **Adımlar:**
  1. Analiz sayfasını aç.
  2. `Genel Bakış` ve `Dağılım & Risk` sekmelerini değiştir.
  3. Grafik ve metrik kartların görünür olduğunu kontrol et.
- **Beklenen sonuç:** Sekme değişiminde grafikler kaybolmaz; sayfa yatay/dikey taşma üretmez.
- **Kanıt:** İki sekmeden ekran görüntüsü.

### ANL-002 | Filtre paneli

- **Adımlar:**
  1. `Filtreleri Gizle/Göster` butonunu kullan.
  2. Portföy kaynağı, para birimi, hisse filtresi ve benchmark seçimini değiştir.
  3. `Analizi Yenile` butonuna bas.
- **Beklenen sonuç:** Filtre paneli state'i doğru görünür; yenileme sonrası grafik ve metrikler seçime göre değişir.
- **Kanıt:** Filtre ve sonuç ekranı.

### ANL-003 | Tarih aralığı ve hızlı tarih butonları

- **Adımlar:**
  1. `1A`, `3A`, `6A`, `1Y`, `Tümü` butonlarını sırayla dene.
  2. Manuel geçerli tarih aralığı gir.
  3. Başlangıç tarihini bitişten sonraya al.
- **Beklenen sonuç:** Hızlı butonlar tarihleri ayarlar; geçersiz aralık uyarı verir ve analiz çalışmaz.
- **Kanıt:** Tarih alanları ve uyarı.

### ANL-004 | Veri eksikliği ve loading

- **Adımlar:**
  1. Fiyat verisi eksik bir hisseyi filtreye dahil et.
  2. Analizi yenile.
  3. Loading sırasında buton metni ve sayfa tepkisini gözle.
- **Beklenen sonuç:** UI donmaz; eksik veri uyarısı anlaşılır; işlem bitince buton eski haline döner.
- **Kanıt:** Uyarı bannerı veya log notu.

---

## 9. Karşılaştırma

### CMP-001 | Varlık seçimi ve normal grafik

- **Adımlar:**
  1. Karşılaştırma sayfasını aç.
  2. En az iki varlık seç.
  3. `Normal` modda ana grafiğin yüklendiğini kontrol et.
- **Beklenen sonuç:** Grafik boş kalmaz; seçilen varlıklar legend/çizgilerde görünür.
- **Kanıt:** Ana grafik ekranı.

### CMP-002 | Normalize ve rasyo modu

- **Adımlar:**
  1. `Normalize (Baz 100)` modunu seç.
  2. `Rasyo Modu`na geç.
  3. Pay ve payda combobox'larının görünür olduğunu kontrol et.
  4. Farklı pay/payda kombinasyonları dene.
- **Beklenen sonuç:** Mod değişimi grafiği yeniler; rasyo kontrolleri yalnızca rasyo modunda görünür.
- **Kanıt:** Üç mod ekranı.

### CMP-003 | Tarih aralığı ve hızlı butonlar

- **Adımlar:**
  1. `1A`, `3A`, `6A`, `1Y`, `YBB`, `Tümü` butonlarını dene.
  2. Manuel geçerli ve geçersiz tarih aralığı gir.
- **Beklenen sonuç:** Tarihler ve grafik senkron güncellenir; geçersiz aralık engellenir.
- **Kanıt:** Tarih alanları.

### CMP-004 | Alt grafik panelleri

- **Adımlar:**
  1. Drawdown, periyodik getiri, scatter ve treemap bölümlerini sırayla görüntüle.
  2. Lazy yüklenen panellerde grafiklerin boş kalmadığını kontrol et.
  3. Sayfa kaydırma ve resize davranışını dene.
- **Beklenen sonuç:** Her panel okunabilir; grafik alanı taşmaz veya üst üste binmez.
- **Kanıt:** Her panelden ekran görüntüsü.

### CMP-005 | Portföy içerik kıyaslama menüleri

- **Adımlar:**
  1. Grafik panellerindeki `Portföy İçeriğini Kıyasla` menüsünü aç.
  2. Global getiri ve portföy seçeneklerini dene.
  3. Menü seçiminin ilgili grafiğe yansıdığını kontrol et.
- **Beklenen sonuç:** Menü seçenekleri doğru aksiyonu tetikler; grafik yenilenir.
- **Kanıt:** Menü ve sonuç grafiği.

### CMP-006 | AI yorum üretimi

- **Adımlar:**
  1. Karşılaştırma sonucu varken AI yorum butonunu kullan.
  2. API anahtarı var ve yok durumlarını ayrı ayrı test et.
- **Beklenen sonuç:** API çalışıyorsa yorum üretilir; yoksa kullanıcıya anlaşılır fallback/hata mesajı gösterilir.
- **Kanıt:** AI paneli veya hata mesajı.

---

## 10. Optimizasyon

### OPT-001 | Kaynak portföy seçimi

- **Adımlar:**
  1. Optimizasyon sayfasını aç.
  2. Ana portföy ve model portföy kaynaklarını sırayla seç.
  3. Boş portföy kaynağı varsa seç.
- **Beklenen sonuç:** Kaynak seçimi doğru label ve veriyle güncellenir; boş kaynak açıklanır.
- **Kanıt:** Kaynak combobox ve boş durum.

### OPT-002 | Optimize etme

- **Adımlar:**
  1. Yeterli fiyat geçmişi olan portföy seç.
  2. `Optimize Et` butonuna bas.
  3. Progress bar ve buton state'ini gözle.
  4. Sonuç metrik kartları ve öneri tablosunu kontrol et.
- **Beklenen sonuç:** Beklenen getiri, risk, Sharpe ve ağırlık önerileri görünür; stale sonuç eski isteğe aitse ekrana yazılmaz.
- **Kanıt:** Sonuç ekranı.

### OPT-003 | Veri yetersizliği ve hata

- **Adımlar:**
  1. Kısa fiyat geçmişi veya tek hisseli kaynak seç.
  2. Optimize etmeyi dene.
  3. Servis hatası veya fiyat lookup hatasını simüle edebiliyorsan gözle.
- **Beklenen sonuç:** Uygulama çökmez; toast/status ile hata açıklanır; eski başarılı sonuç yanlışlıkla korunmaz.
- **Kanıt:** Hata mesajı.

---

## 11. Finansal Planlama

### FP-BUD-001 | Bütçe ay seçimi

- **Adımlar:**
  1. Finansal Planlama > Bütçe Yönetimi sekmesini aç.
  2. Kayıtlı bütçesi olan bir ay seç.
  3. Kayıtlı bütçesi olmayan bir ay seç.
- **Beklenen sonuç:** Kayıtlı ayda kayıtlı içerik korunur; boş ayda form taslak olarak açılır.
- **Kanıt:** İki ayın ekran görüntüsü.

### FP-BUD-002 | Gelir/gider satırı ekleme ve silme

- **Adımlar:**
  1. Gelir bölümüne satır ekle, başlık ve tutar gir.
  2. Gider bölümüne satır ekle, başlık ve tutar gir.
  3. Her iki bölümden satır sil.
- **Beklenen sonuç:** Satırlar doğru bölümde oluşur; toplamlar canlı güncellenir; silme toplamları azaltır.
- **Kanıt:** Satır ve özet kartları.

### FP-BUD-003 | Bütçe kaydetme

- **Adımlar:**
  1. Gelir, gider ve aylık tasarruf hedefi gir.
  2. `Bütçeyi Kaydet` butonuna bas.
  3. Ay değiştirip geri dön.
- **Beklenen sonuç:** Kayıtlı veriler geri yüklenir; status label başarılı kayıt bilgisini gösterir.
- **Kanıt:** Kaydetme sonrası ve yeniden yükleme ekranı.

### FP-BUD-004 | Aylık Tasarruf Hedefi TL formatı

- **Adımlar:**
  1. `Aylık Tasarruf Hedefi` alanına `300000` gir.
  2. Alan odağını değiştir.
  3. Kaydet ve ayı yeniden aç.
- **Beklenen sonuç:** Görsel format `300.000,00TL` şeklindedir; kayıt numeric değeri bozulmaz.
- **Kanıt:** Spinbox ekran görüntüsü.

### FP-BUD-005 | Pin/unpin davranışı

- **Adımlar:**
  1. Gelir satırında bir başlık ve tutar gir, pin ikonuna bas.
  2. Gider satırında başka bir başlık ve tutar gir, pin ikonuna bas.
  3. İkonların aktif göründüğünü kontrol et.
  4. Aynı kalemi unpin yap.
- **Beklenen sonuç:** Pin state'i ikonla görünür; unpin sonrası kalem pinli kabul edilmez.
- **Kanıt:** Aktif/pasif ikon ekranları.

### FP-BUD-006 | Pinli kalemlerin boş aya otomatik gelmesi

- **Adımlar:**
  1. En az bir gelir ve bir gider kalemini pinle.
  2. Daha önce bütçe kaydedilmemiş bir ay seç.
  3. Forma otomatik gelen satırları kontrol et.
- **Beklenen sonuç:** Pinli kalemler varsayılan tutarlarıyla gelir/gider bölümlerine eklenir.
- **Kanıt:** Boş ay otomatik taslak ekranı.

### FP-BUD-007 | Kayıtlı ayın korunması

- **Adımlar:**
  1. Bir ay için bütçe kaydet.
  2. Sonra yeni bir pinli kalem oluştur.
  3. Kayıtlı aya geri dön.
- **Beklenen sonuç:** Kayıtlı ay sessizce değiştirilmez; yeni pinli kalem kayıtlı ayın içine otomatik enjekte edilmez.
- **Kanıt:** Kayıtlı ay ekranı.

### FP-GOAL-001 | Hedef oluşturma

- **Adımlar:**
  1. Hedef Takibi sekmesini aç.
  2. `Yeni Hedef` ile hedef adı, hedef tutar, mevcut tutar ve tarih gir.
  3. Boş ad, negatif tutar ve geçersiz tarih dene.
- **Beklenen sonuç:** Geçerli hedef tabloya eklenir; geçersiz girişler engellenir.
- **Kanıt:** Hedef tablosu.

### FP-GOAL-002 | Katkı ekleme ve silme

- **Adımlar:**
  1. Bir hedef seç.
  2. `Katkı Ekle` ile tutar gir.
  3. Güncel tutar/progress değerini kontrol et.
  4. Hedefi silme akışında iptal ve onay seçeneklerini dene.
- **Beklenen sonuç:** Katkı progress'i artırır; iptal silmez; onay hedefi kaldırır.
- **Kanıt:** Önce/sonra hedef satırı.

### FP-GOAL-003 | Fizibilite analizi

- **Adımlar:**
  1. Deadline ve hedef tutarı olan bir hedef seç.
  2. `Fizibilite Analizi` çalıştır.
  3. Aylık gerekli katkı ve durum mesajını kontrol et.
- **Beklenen sonuç:** Analiz anlaşılır sonuç verir; eksik veri varsa kullanıcıya açıklanır.
- **Kanıt:** Analiz sonucu.

---

## 12. Risk Profili

### RISK-001 | Profil yok başlangıç durumu

- **Adımlar:**
  1. Test DB'de risk profili yokken sayfayı aç.
  2. Başlangıç kartı ve ilk soru görünümünü kontrol et.
- **Beklenen sonuç:** Kullanıcı ankete başlayabilir; boş profil hata üretmez.
- **Kanıt:** İlk ekran.

### RISK-002 | Anket ilerleme ve zorunlu cevap

- **Adımlar:**
  1. Cevap seçmeden `Devam` butonuna bas.
  2. Bir cevap seçip ilerle.
  3. `Geri` butonuyla önceki soruya dön.
- **Beklenen sonuç:** Cevapsız ilerleme engellenir; cevap seçimi korunur; geri dönüş çalışır.
- **Kanıt:** Uyarı ve ilerleme ekranları.

### RISK-003 | Profil hesaplama

- **Adımlar:**
  1. Tüm soruları cevapla.
  2. `Profili Hesapla` butonuna bas.
  3. Başarı mesajı, skor, profil etiketi, boyut skorları, varlık dağılımı ve uygunluk notlarını kontrol et.
- **Beklenen sonuç:** Profil kaydedilir ve tekrar girişte sonuç kartı görünür.
- **Kanıt:** Sonuç kartı.

---

## 13. AI Asistan

### AI-001 | Sayfa açılışı ve backend durumu

- **Adımlar:**
  1. AI Asistan sayfasını aç.
  2. Bağlantı kontrolü/loading durumunu gözle.
  3. Backend yokken fallback/mock davranışını kontrol et.
- **Beklenen sonuç:** Sayfa UI thread'i bloklamaz; backend yoksa kullanıcıya anlaşılır durum gösterir.
- **Kanıt:** Status bannerı.

### AI-002 | Model analiz paneli

- **Adımlar:**
  1. Geçerli ticker gir.
  2. Analiz çalıştır.
  3. Tahmin, sinyal, performans ve XAI kartlarını kontrol et.
  4. Geçersiz ticker dene.
- **Beklenen sonuç:** Geçerli analiz sonuç üretir; geçersiz ticker hata mesajı üretir.
- **Kanıt:** Analiz sonucu ve hata ekranı.

### AI-003 | Analizi chate gönderme

- **Adımlar:**
  1. Başarılı analiz sonrası `SendToChatButton` aksiyonunu kullan.
  2. Chat panelinde yapılandırılmış sistem mesajının göründüğünü kontrol et.
- **Beklenen sonuç:** Analiz bağlamı chat tarafına taşınır; mesaj formatı bozulmaz.
- **Kanıt:** Chat mesajı.

### AI-004 | Chatbot paneli

- **Adımlar:**
  1. Metin mesajı gönder.
  2. Boş mesaj göndermeyi dene.
  3. `Sohbeti Temizle` aksiyonunu kullan.
  4. Gemini API anahtarı yoksa hata/fallback davranışını gözle.
- **Beklenen sonuç:** Boş mesaj engellenir; yanıt veya hata net görünür; temizleme sohbeti sıfırlar.
- **Kanıt:** Chat ekranı.

---

## 14. Ayarlar

### SET-001 | Otomatik fiyat yenileme

- **Adımlar:**
  1. `Otomatik fiyat yenileme` checkbox'ını aç/kapat.
  2. Aralık combobox'ından 5/15/30/60 dakika seçeneklerini dene.
  3. Uygulamayı yeniden açıp tercihin korunmasını kontrol et.
- **Beklenen sonuç:** Timer ayarı restart gerektirmeden uygulanır; tercih kalıcıdır.
- **Kanıt:** Ayar ekranı.

### SET-002 | Görünüm

- **Adımlar:**
  1. Görünüm sekmesinde dark/light tema kartlarını sırayla seç.
  2. Tüm ana sayfalarda tema görünümünü kontrol et.
- **Beklenen sonuç:** Tema anında değişir; kart seçimi doğru state gösterir.
- **Kanıt:** Tema kartı ve başka sayfa ekranı.

### SET-003 | Sistem sıfırlama

- **Ön koşul:** Sadece test DB veya yedek alınmış DB.
- **Adımlar:**
  1. Ana Sayfa sekmesindeki `Sistemi Sıfırla` aksiyonunu başlat.
  2. Onay penceresinde iptal et.
  3. Tekrar başlat ve onayla.
  4. Uygulama verilerinin beklenen şekilde temizlendiğini kontrol et.
- **Beklenen sonuç:** İptal veri silmez; onay test DB'yi sıfırlar; uygulama çökmez.
- **Kanıt:** Onay öncesi/sonrası ekranı.

### SET-004 | Fiyat Verisi Yönetimi - analiz

- **Adımlar:**
  1. Fiyat Verisi Yönetimi sekmesini aç.
  2. Kapsam combobox'ında tüm aktif portföyler, ana portföy ve model portföy seçeneklerini dene.
  3. Başlangıç/bitiş tarihlerini ayarla.
  4. `Sadece problemli kayıtlar` seçeneğini aç/kapat.
  5. `Analiz Et` butonuna bas.
- **Beklenen sonuç:** Tablo ve detay metni seçili kapsama göre güncellenir; tarih aralığı validasyonu çalışır.
- **Kanıt:** Analiz tablosu.

### SET-005 | Fiyat Verisi Yönetimi - güncelleme ve silme

- **Ön koşul:** Test DB veya yedek alınmış DB.
- **Adımlar:**
  1. `Toplu Eksikleri Güncelle` aksiyonunu çalıştır.
  2. Bir satır seçip `Seçili Hisseyi Güncelle` çalıştır.
  3. `Son Günden Bugüne Güncelle` aksiyonunu dene.
  4. Test aralığında `Aralığı Sil` için iptal ve onay davranışını dene.
  5. `Raporu Kopyala` ile clipboard içeriğini kontrol et.
- **Beklenen sonuç:** Güncelleme aksiyonları status verir; silme yalnız onayda çalışır; rapor kopyalanır.
- **Kanıt:** Status mesajı ve clipboard notu.

### SET-006 | Kurumsal Aksiyonlar

- **Ön koşul:** Test DB veya yedek alınmış DB.
- **Adımlar:**
  1. `KAP/MKK Yenile` ve `Listeyi Yenile` aksiyonlarını çalıştır.
  2. Aday seç, detay metnini kontrol et.
  3. `Düzenle` dialogunda alanları değiştir ve iptal/kaydet davranışlarını dene.
  4. `Yoksay` için iptal/onay akışını dene.
  5. `Onayla ve Uygula` aksiyonunu test adayında çalıştır.
  6. `Kaynağı Aç` aksiyonunda bağlantı davranışını kontrol et.
- **Beklenen sonuç:** Kaynak erişilemezse graceful uyarı verilir; aday uygulama portföy/fiyat verisini beklenen şekilde değiştirir; iptal veri yazmaz.
- **Kanıt:** Aday tablosu ve uygulama sonrası sonuç.

---

## 15. Çapraz Akışlar

### XFLOW-001 | Fiyat güncelleme event yayılımı

- **Adımlar:**
  1. Dashboard'da fiyat güncelle.
  2. Model Portföyler, Analiz, Karşılaştırma ve Hisse Detayı sayfalarına geç.
  3. Güncel fiyatların veya ilgili uyarıların yansımasını kontrol et.
- **Beklenen sonuç:** Fiyat event'i stale veri bırakmaz; sayfalar kendi veri sözleşmesine göre yenilenir.
- **Kanıt:** Önce/sonra ekran görüntüleri.

### XFLOW-002 | Export dosyaları

- **Adımlar:**
  1. Dashboard ve Model Portföyler raporlarını üret.
  2. Excel dosyalarını aç.
  3. Başlıklar, tarih aralığı, sayısal formatlar ve boş satırları kontrol et.
- **Beklenen sonuç:** Dosyalar bozuk değildir; rapor kapsamı seçime uygundur.
- **Kanıt:** Dosya adı ve kısa içerik notu.

### XFLOW-003 | Silme/onay genel davranışı

- **Adımlar:**
  1. Watchlist, model portföy, finansal hedef, fiyat aralığı ve sistem reset onaylarını ayrı ayrı test et.
  2. Her akışta önce iptal, sonra onay dene.
- **Beklenen sonuç:** İptal hiçbir veri yazmaz; onay yalnız hedeflenen veriyi etkiler.
- **Kanıt:** Her akış için önce/sonra notu.

### XFLOW-004 | Yeniden başlatma sonrası kritik state

- **Adımlar:**
  1. Tema, otomatik yenileme, watchlist sırası, model portföy seçimi, bütçe kayıtları ve risk profilini değiştir.
  2. Uygulamayı kapatıp aç.
  3. State'lerin korunup korunmadığını kontrol et.
- **Beklenen sonuç:** Kalıcı state'ler korunur; geçici worker/loading state'leri temiz başlar.
- **Kanıt:** Yeniden açılış ekranları.

---

## 16. Negatif ve Hata Senaryoları

### NEG-001 | Boş veri

- **Adımlar:** Boş DB veya reset sonrası tüm ana sayfaları aç.
- **Beklenen sonuç:** Hiçbir sayfa crash etmez; boş durum mesajları ve aksiyonları görünür.
- **Kanıt:** Boş sayfa ekranları.

### NEG-002 | Geçersiz tarih aralıkları

- **Adımlar:** Dashboard rapor, Analiz, Karşılaştırma, Ayarlar fiyat verisi ve Finansal Planlama dialoglarında başlangıç tarihini bitişten sonraya al.
- **Beklenen sonuç:** İşlem çalışmaz; kullanıcıya net uyarı verilir.
- **Kanıt:** Uyarı mesajları.

### NEG-003 | Yetersiz nakit veya pozisyon

- **Adımlar:** Dashboard, Hisse Detayı ve Model Portföyler içinde bakiyeden fazla alış veya elde olmayan lot satışı dene.
- **Beklenen sonuç:** Geçersiz işlem yazılmaz; uyarı verilir.
- **Kanıt:** Uyarı ve işlem geçmişinin değişmediği notu.

### NEG-004 | Dış servis hataları

- **Adımlar:** Fiyat lookup, KAP/MKK yenileme ve AI/Gemini çağrılarını ağ yok veya API anahtarı yok durumunda dene.
- **Beklenen sonuç:** Uygulama kapanmaz; fallback veya hata mesajı görünür; logda beklenen warning dışında kritik exception olmaz.
- **Kanıt:** Hata mesajı ve log satırı.

### NEG-005 | Kullanıcı iptali

- **Adımlar:** Tüm dialoglarda pencere kapatma, İptal ve Escape davranışını dene.
- **Beklenen sonuç:** İptal edilen aksiyon veri yazmaz; kaynak sayfa kullanılabilir kalır.
- **Kanıt:** Dialog kapandıktan sonra veri state'i.

---

## 17. Sürüm Öncesi Smoke Checklist

Tam manuel test yapılamadığında en az şu hızlı kontrol çalıştırılmalıdır:

- [ ] Uygulama `python app.py` ile açılıyor, logda kritik exception yok.
- [ ] Tüm ana sayfalara gidilebiliyor.
- [ ] Dashboard portföy kartları ve tablo görünüyor.
- [ ] Yeni alış işlemi eklenebiliyor.
- [ ] Sermaye yatırma/çekme çalışıyor.
- [ ] Watchlist oluşturma ve hisse ekleme çalışıyor.
- [ ] Model portföy oluşturma, hisse al/sat ve rapor alma çalışıyor.
- [ ] Hisse Detayı dashboard ve model portföy bağlamından açılıyor.
- [ ] Analiz sayfasında tarih/benchmark değiştirip yenileme çalışıyor.
- [ ] Karşılaştırma sayfasında normal, normalize ve rasyo modları grafik üretiyor.
- [ ] Optimizasyon yeterli veriyle sonuç üretiyor veya yetersiz veri için düzgün hata veriyor.
- [ ] Finansal Planlama bütçe kaydediyor, pinli kalemleri boş aya getiriyor ve `300.000,00TL` formatını gösteriyor.
- [ ] Finansal hedef ekleme ve katkı ekleme çalışıyor.
- [ ] Risk profili anketi tamamlanıp sonuç kartı üretiyor.
- [ ] AI Asistan backend yoksa fallback/hata state'ini düzgün gösteriyor.
- [ ] Ayarlar tema değişimi ve otomatik fiyat yenileme tercihini kaydediyor.
- [ ] Fiyat Verisi Yönetimi analiz raporu üretiyor.
- [ ] Kurumsal aksiyon aday listesi hata durumunda uygulamayı çökertmiyor.
- [ ] Uygulama kapatılıp açıldığında kalıcı state'ler korunuyor.

---

## 18. Test Kapanışı

- Başarısız testler için ID, ekran görüntüsü, log ve tekrar üretme adımlarıyla issue/not oluştur.
- Yıkıcı testler yapıldıysa DB'yi yedekten geri yükle veya test DB'yi yeniden seed et.
- Export, screenshot ve geçici dosyaları test koşumu klasöründe sakla.
- Tam test koşumunun sonunda şu özet kaydı üret:

```text
Manuel Test Özeti
Tarih:
Branch / Commit:
DB:
Toplam Senaryo:
Geçti:
Kaldı:
Engellendi:
Kritik Bulgular:
Yedek / Temizlik:
```
