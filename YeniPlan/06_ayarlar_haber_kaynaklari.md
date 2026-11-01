# 06 — Ayarlar > Haber Kaynakları

> Ana sayfa: [index.md](index.md) | Günlük: [log.md](log.md) | Önceki: [05_genel_bakis_ve_haber.md](05_genel_bakis_ve_haber.md) | Sonraki: [07_test_ve_kalite.md](07_test_ve_kalite.md)

Durum: **Taslak** (Aşama 7)

Kullanıcı istediği haber kaynağını Ayarlar sayfasından kapatabilir; örneğin KAP'tan bildirim almak istemiyorsa kaynağı kapatır.

## 1. Arayüz

`SettingsView`'e yeni sekme: `SettingsNewsTab.qml`.

| Bölüm | İçerik |
|---|---|
| Kaynak listesi | KAP bildirimleri, yfinance haberleri ve her RSS beslemesi için ad, açıklama, dil, aç/kapa anahtarı |
| Özel RSS | Besleme adı + adresi ekleme, silme; adres doğrulama ("Bağlantıyı test et") |
| Yenileme aralığı | Haber panelinin otomatik yenileme süresi (varsayılan yaklaşık 10 dakika) |
| Durum | Her kaynak için son başarılı çekim zamanı ve son hata |

Kapatılan kaynak hemen etkili olur: `NewsController.sourcesChanged` sinyali paneli yeniler, kapalı kaynağın önbelleklenmiş haberleri gösterilmez.

## 2. Controller

`NewsSettingsController` (ayrı dosya; `SettingsController` şişmesin diye):

- `sources` (model): kaynak kimliği, ad, etkin mi, durum.
- `setSourceEnabled(sourceId, enabled)`, `addRssFeed(name, url)`, `removeRssFeed(sourceId)`, `testSource(sourceId)`, `setRefreshInterval(minutes)`.
- Ağ gerektiren `testSource` arka planda çalışır, sonucu Signal ile döner.
- Yalnızca `NewsService` / tercih portu üzerinden çalışır; repository'e doğrudan erişmez.

## 3. Veri

SQLite `news_source_settings`:

| Sütun | Anlam |
|---|---|
| `source_id` (PK) | `kap`, `yfinance`, `rss:<kimlik>` |
| `enabled` | Açık/kapalı |
| `config_json` | RSS adresi, ad, dil; yenileme aralığı gibi kaynak ayarları |

İlk çalıştırmada varsayılan kaynaklar eklenir: KAP ve yfinance etkin; Türkçe RSS kaynakları spike sonucuna göre varsayılan listeye girer.

## 4. Metin ve Kalite Kuralları

- Tüm metinler `Strings.qml` içinde, doğru Türkçe karakterlerle; kullanılmayan anahtar bırakılmaz (`test_strings_catalog.py`).
- Sabit piksel genişlikli düğme yok; dar pencerede taşma olmaz (`ScrollView`).
- Anahtar bileşenleri mevcut tema bileşenlerinden kurulur.

## 5. Testler

- `NewsSettingsController`: aç/kapa kalıcılığı, geçersiz RSS adresi, kaynak silme, test sonucu sinyali.
- `NewsService` ile entegrasyon: kapatılan kaynağın çağrılmaması.
- QML: sekme uyarısız yüklenir, anahtar durumu modele yansır.
