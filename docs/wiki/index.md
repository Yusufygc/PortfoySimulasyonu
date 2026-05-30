# Wiki — İçerik Kataloğu

> Bu dosya tüm wiki sayfalarının dizinidir. Oturum başında okunur; ilgili sayfalar buradan bulunur.  
> Değişiklik günlüğü: [log.md](log.md)

---

## Mimari ve Teknik

| Sayfa | Özet |
|-------|------|
| [architecture.md](architecture.md) | Katmanlı mimari (Clean Architecture), tüm domain modelleri, servisler, DB şeması, veri akışı, optimizasyon motoru |

---

## Operasyon ve Süreç

| Sayfa | Özet |
|-------|------|
| [log.md](log.md) | Kronolojik, yalnızca ekleme yapılan wiki güncelleme ve commit kaydı |
| [Plans.md](Plans.md) | Gelecek geliştirmeler, notlar ve code review ihtiyaçları |

---

## Proje Genel Bakış

**Portföy Simülasyonu** — PyQt5 masaüstü portföy yönetim uygulaması.

- YFinance ile gerçek zamanlı fiyat takibi
- Markowitz optimizasyonu (SciPy + Ledoit-Wolf)
- BIST ve küresel hisse desteği
- Model/sanal portföy simülasyonu ve backtest
- Risk profili analizi, Excel raporlama, Gemini AI entegrasyonu

Geliştirme komutları ve kurulum için bkz. [../../CLAUDE.md](../../CLAUDE.md).  
Commit ve wiki kuralları için bkz. [../../RULES.md](../../RULES.md).

---

## Sayfa Ekleme Talimatı

Yeni wiki sayfası oluşturulduğunda:
1. Bu tabloya bir satır ekle
2. `log.md`'ye `yeni-sayfa` girişi ekle
3. Yeni sayfanın üstüne navigation satırı ekle

---

*Son güncelleme: 2026-05-09 — Wiki sistemi başlatıldı, LLM Wiki pattern uygulandı.*
