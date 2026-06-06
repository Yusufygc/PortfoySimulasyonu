# RULES.md — Proje Kuralları ve Wiki Standartları

Bu dosya, projedeki oturum yönetimi, wiki bakımı ve LLM/Ajan iş akışları için bağlayıcı ana kuralları tanımlar. Diğer operasyonel kurallar için ilgili kılavuzlara bağlantı içerir.

---

## 0. Oturum Başlangıç Kuralları

Her ajan/LLM oturumu, kod veya plan üretmeden önce proje kökündeki `AGENTS.md` ve `CLAUDE.md` dosyalarını okur. `AGENTS.md` yerel ajan giriş noktasıdır; `CLAUDE.md` proje bağlamını ve bu `RULES.md` dosyasına yönlendirmeyi taşır.

Dosyalar arasında çelişki olursa en dar kapsamlı ve kullanıcıya en yakın talimat uygulanır; güvenlik, commit ve wiki kuralları için bu dosyadaki bağlayıcı hükümler korunur.

### 0.1 Python Ortamı Kullanımı

Tüm python komutları (test çalıştırma, script yürütme vb.) için **KESİNLİKLE** `C:\Users\ysfygc\anaconda3\envs\Fintech\python.exe` yolu kullanılarak `Fintech` conda ortamı üzerinden işlem yapılmalıdır. Base python veya sadece `python` komutu kullanılmamalıdır.

---

## 1. Wiki Güncelleme Kuralları

### 1.1 Temel İlke

`docs/wiki/` bir **kalıcı, biriken bilgi tabanıdır** — sohbet geçmişi değil.  
Ham kaynak (kod, commit, konuşma) değiştiğinde wiki güncellenmeli; wiki hiçbir zaman eskimemelidir.

Her oturumun başında `docs/wiki/index.md` okunur. Sorular bu katalogdan ilgili sayfalar bulunarak yanıtlanır.

### 1.2 Hangi Durumda Wiki Güncellenir?

| Durum | Hangi Dosya(lar) |
|-------|-----------------|
| Yeni özellik eklendi | `architecture.md` (ilgili bölüm) + `log.md` |
| Mimari karar verildi | `architecture.md` + `log.md` |
| Büyük refaktör yapıldı | `architecture.md` + `log.md` |
| Yeni wiki sayfası oluşturuldu | `index.md` (kataloga eklenir) + `log.md` |
| Hata çözümü kalıcı bir ders içeriyorsa | Yeni sayfa veya `architecture.md` notu + `log.md` |
| Planlanan özellik netleşti | `architecture.md` (Roadmap bölümü) + `log.md` |
| Oturum sona eriyor, önemli bilgi konuşuldu | Tüm ilgili sayfalar + `log.md` |

Küçük kod düzeltmeleri, stil değişiklikleri, yazım hatası düzeltmeleri wiki güncellemesi gerektirmez.

### 1.3 `index.md` Kuralları

`index.md` **içerik odaklı katalogdur** — tüm wiki sayfalarını listeler.

- Her sayfa bir satır: `- [Sayfa Adı](sayfa.md) — tek cümle özet`
- Kategorilere göre gruplandırılır (Mimari, Operasyonlar, Kaynaklar vb.)
- Her yeni sayfa oluşturulduğunda veya silindiğinde güncellenir
- LLM, sorguya cevap vermeden önce bu dosyayı okuyarak hangi sayfaların ilgili olduğunu belirler

### 1.4 `log.md` Kuralları

`log.md` **kronolojik, yalnızca ekleme yapılan** kayıttır.

**Format (zorunlu):**
```
## [YYYY-AA-GG] işlem | Konu Başlığı

- Yapılan değişiklik veya kararın kısa açıklaması
- Etkilenen dosyalar (varsa)
- Bağlantılı sayfa (varsa): [architecture.md](architecture.md)
```

**Geçerli işlem türleri:**
- `ingest` — yeni kaynak/bilgi wiki'ye işlendi
- `güncelleme` — mevcut sayfa güncellendi
- `yeni-sayfa` — yeni wiki sayfası oluşturuldu
- `lint` — wiki sağlık kontrolü yapıldı
- `sorgu` — önemli bir soru soruldu ve yanıt wiki'ye kaydedildi
- `commit` — anlamlı bir commit atıldı

Eski girişler **asla silinmez veya düzenlenmez**. Yeni girişler en üste eklenir.

Grep ile log analizi: `grep "^## \[" docs/wiki/log.md | head -10`

### 1.5 `architecture.md` Kuralları

- Katman açıklamaları, veritabanı şeması ve veri akışları burada tutulur
- Modül eklenince/silinince ilgili tablo güncellenir
- Mimari kararların "neden" kısmı mutlaka yazılır
- Diğer wiki sayfalarına anchor link ile referans verilir

### 1.6 Yeni Wiki Sayfası Oluşturma

1. `docs/wiki/<konu>.md` dosyası oluşturulur
2. Dosyanın üstüne navigation satırı eklenir: `> Ana sayfa: [index.md](index.md) | ...`
3. `index.md` kataloğuna eklenir
4. `log.md`'ye `yeni-sayfa` girişi eklenir
5. İlgili mevcut sayfalara cross-reference eklenir

### 1.7 Lint (Sağlık Kontrolü)

Periyodik olarak aşağıdaki soruları sor ve düzelt:

- Gelen linki olmayan (orphan) sayfa var mı?
- Eski bilgi içeren bölüm var mı (kodla çelişiyor mu)?
- `index.md`'de olmayan ama `docs/wiki/`'de var olan sayfa var mı?
- Önemli bir kavram bahsediliyor ama kendi sayfası yok mu?
- Cross-reference eksik mi?

---

## 3. LLM Wiki Operasyon Protokolü

Bu proje **LLM Wiki** pattern'ini uygular: ham kaynak değişmez, LLM wiki'yi yazar ve bakımını yapar, insan yönlendirir ve soru sorar.

### 3.1 Ingest (Yeni Bilgi Ekleme)

Yeni bir kaynak (kod kararı, harici makale, toplantı notu vb.) bilgi tabanına eklenecekse:

1. Kaynak okunur / tartışılır
2. Önemli kararlar ve öğrenilenler çıkarılır
3. İlgili wiki sayfaları güncellenir (10-15 sayfaya dokunabilir)
4. Gerekirse yeni sayfa açılır
5. `index.md` güncellenir
6. `log.md`'ye `ingest` girişi eklenir

### 3.2 Sorgu (Query)

Bir soru sorulduğunda:

1. `index.md` okunur → ilgili sayfalar belirlenir
2. İlgili sayfalar okunur
3. Yanıt bu bilgilerden sentezlenir
4. Eğer yanıt anlamlı ve kalıcıysa `log.md`'ye `sorgu` girişi eklenir; gerekirse yeni sayfa açılır

### 3.3 Lint (Sağlık Kontrolü)

Periyodik olarak (yaklaşık 10 ingest'te bir) wiki sağlık kontrolü yapılır.  
Sonuçlar `log.md`'ye `lint` girişi olarak kaydedilir.

---

## 6. Kapsam Dışı

Bu kurallar aşağıdakiler için geçerli **değildir**:

- Küçük kod düzeltmeleri (yazım hatası, tek satır fix)
- Test çalıştırma çıktıları
- Geçici araştırma sohbetleri (wiki'ye işlenmedikçe)

---

## 🔗 İlgili Diğer Kurallar ve Kılavuzlar
- Geliştirme, Branch Yönetimi, Commit ve PR süreçleri için: [GOVERNANCE.md](GOVERNANCE.md)
- Kod kalitesi, refactor limitleri, dizin konvansiyonları ve test kapıları için: [ARCHITECTURE_GATES.md](ARCHITECTURE_GATES.md)
