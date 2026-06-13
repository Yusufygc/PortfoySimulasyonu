# Kod Kalitesi Guardrail'leri

> Ana sayfa: [index.md](index.md) | Baseline: [code_quality_baseline_2026-06-13.md](code_quality_baseline_2026-06-13.md) | Test stratejisi: [testing_strategy.md](testing_strategy.md)

Bu sayfa `PortfoySimulasyonu_saglik_raporu.html` sonrası kalıcı kalite kurallarını tanımlar. HTML raporu tek karar kaynağı değildir; refactor hedefleri `scripts/measure_code_quality.py` çıktısı ve mevcut mimari kurallarla doğrulanır.

## Ölçüm Komutu

```bash
C:\Users\ysfygc\anaconda3\envs\Fintech\python.exe scripts\measure_code_quality.py
```

Script şu dosyaları üretir:

- [code_quality_baseline_2026-06-13.md](code_quality_baseline_2026-06-13.md)
- [code_quality_baseline_2026-06-13.json](code_quality_baseline_2026-06-13.json)

Ölçümde yorum satırları ve boş satırlar eşik kararından çıkarılır. Modül, sınıf ve fonksiyon docstring satırları ayrıca raporlanır; eşikler `effective_code_lines` üzerinden değerlendirilir.

## Eşikler

| Yüzey | Eşik | Aksiyon |
|---|---:|---|
| Sınıf satırı | `>300` effective satır | Yeni davranış eklemeden önce panel, helper veya servis ayrımı yapılır. |
| Sınıf metodu | `>20` metot | Sorumluluk ayrımı yapılır veya geçici istisna belgelenir. |
| Fonksiyon/metot satırı | `>50` effective satır | Küçük helper fonksiyonlara bölünür. |
| Fonksiyon/metot parametresi | `>5` effective parametre | Parametre nesnesi, config modeli veya daha dar API tercih edilir. |
| Cyclomatic complexity | `>10` | Koşul dalları ayrıştırılır ve hedefli test eklenir. |
| UI page dosyası | `>400` effective satır | Page yalnız layout/wiring bırakılacak şekilde panel/component ayrımı yapılır. |

## İstisna Protokolü

- Yeni istisna ancak geçici ve gerekçeli ise kabul edilir.
- İstisna `tests/ui/test_refactor_guards.py` veya ölçüm JSON'unda görünür olmalı, bu sayfada veya ilgili wiki sayfasında refactor hedefiyle açıklanmalıdır.
- Production dosyalarında yeni eşik ihlali oluşturulmaz. Zorunluysa aynı değişiklik setinde refactor planı ve test kapsamı eklenir.
- Repository interface'leri için "God Object" uyarıları false-positive olabilir; yalnız interface gerçekten farklı iş alanlarını karıştırıyorsa bölünür.

## UI Page ve Component Standardı

UI page sınıfları yalnız sayfa iskeleti, signal wiring ve servis/panel bağlantısından sorumludur. Aşağıdaki davranışlar page içinde büyütülmez:

- Büyük `_init_ui` blokları
- Tablo satırı doldurma ve formatlama
- Chart çizimi ve tema uyarlama
- Worker orchestration
- Dialog içi validasyon ve çok adımlı form akışı

Bu davranışlar `widgets/`, `panels/`, `utils/` veya sayfaya özel alt modüllere taşınır. Kullanıcıya görünen metinler `src/ui/shared/locale_tr.py` içindeki `L10N` üzerinden gelir.

## Application Service Facade Standardı

Application servisleri public API'yi koruyan ince facade olarak kalmalıdır. Aşağıdaki sorumluluklar büyüyen servislerden ayrılır:

- Scope ve input çözümleme
- Validasyon
- Dış provider/repository çağrısı
- Hesaplama/analiz algoritması
- Persistence ve rapor DTO üretimi

Öncelikli refactor hedefleri baseline raporunda listelenen fiyat sağlığı, model portföy trade, kurumsal aksiyon, risk profili ve optimizasyon servisleridir.

## Yeni Özellik Öncesi Kontrol

1. Ölçüm script'ini çalıştır.
2. Değiştirilecek dosyada mevcut eşik ihlali varsa önce refactor dilimini planla.
3. Yeni kullanıcı metinlerini `L10N` içine ekle.
4. Katman sınırlarını koru; UI doğrudan HTTP/SDK/client import etmez.
5. Hedefli testleri ve sonunda tam `pytest tests -q` komutunu çalıştır.
