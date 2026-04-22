# src/ui/styles/tokens.py
"""
Design Token Sistemi - Portföy Simülasyonu

Bu dosya uygulamanın tüm görsel sabitlerini (Design Tokens) merkezi
olarak tanımlar. QSS dosyalarında @token_adı formatında referans
verilir; ThemeManager bu değerleri runtime'da QSS'e enjekte eder.

HOW IT WORKS:
  QSS dosyalarında:   background-color: @COLOR_BG_SURFACE;
  Bu dosyada:         "COLOR_BG_SURFACE": "#1e293b",
  ThemeManager bunu:  background-color: #1e293b;  şeklinde yerine koyar.

NASIL YENİ TEMA EKLENIR:
  1. Bu dosyada LIGHT_THEME dict'ini oluştur.
  2. ThemeManager.apply_theme(app, token_overrides=LIGHT_THEME) ile uygula.
"""

# ============================================================
#  DARK THEME TOKENS (Varsayılan)
# ============================================================
DARK_THEME: dict[str, str] = {

    # -----------------------------------------------------------
    # BACKGROUND (Arka Plan Katmanları)
    # -----------------------------------------------------------
    "COLOR_BG_BASE":        "#0f172a",   # En derin arka plan (sayfa zemini)
    "COLOR_BG_SURFACE":     "#1e293b",   # Kartlar, paneller (zemine bir kat üst)
    "COLOR_BG_ELEVATED":    "#334155",   # Hover, seçili satır (en üst katman)
    "COLOR_BG_OVERLAY":     "#475569",   # Tooltip, dropdown overlay

    # -----------------------------------------------------------
    # BORDERS
    # -----------------------------------------------------------
    "COLOR_BORDER":         "#334155",   # Standart kenar çizgisi
    "COLOR_BORDER_SUBTLE":  "#1e293b",   # Hafif ayraçlar, tablo gridleri

    # -----------------------------------------------------------
    # TEXT (Metin Renkleri)
    # -----------------------------------------------------------
    "COLOR_TEXT_PRIMARY":   "#f1f5f9",   # Birincil metin (başlıklar)
    "COLOR_TEXT_SECONDARY": "#94a3b8",   # İkincil metin (alt yazılar)
    "COLOR_TEXT_MUTED":     "#64748b",   # Soluk metin (zaman damgaları)
    "COLOR_TEXT_BODY":      "#cbd5e1",   # Gövde metni
    "COLOR_TEXT_BRIGHT":    "#f8fafc",   # Parlak beyaz metin
    "COLOR_TEXT_WHITE":     "white",     # Buton üzeri metin

    # -----------------------------------------------------------
    # BRAND / PRIMARY (Marka Rengi)
    # -----------------------------------------------------------
    "COLOR_PRIMARY":        "#3b82f6",   # Ana mavi (butonlar, seçili tab)
    "COLOR_PRIMARY_HOVER":  "#2563eb",   # Hover durumu
    "COLOR_PRIMARY_DARK":   "#1d4ed8",   # Aktif / pressed durumu

    # -----------------------------------------------------------
    # ACCENT (Vurgu - AI ve navigasyon rengi)
    # -----------------------------------------------------------
    "COLOR_ACCENT":         "#00D4FF",   # Cyan vurgu (AI, nav active)
    "COLOR_ACCENT_HOVER":   "#38bdf8",   # Hover durumu
    "COLOR_ACCENT_LIGHT":   "#7dd3fc",   # Açık cyan

    # -----------------------------------------------------------
    # SUCCESS (Alış / Pozitif)
    # -----------------------------------------------------------
    "COLOR_SUCCESS":        "#10b981",   # Yeşil (Al butonu, kâr)
    "COLOR_SUCCESS_HOVER":  "#059669",   # Hover
    "COLOR_SUCCESS_BRIGHT": "#22c55e",   # Parlak yeşil (radio indicator)
    "COLOR_SUCCESS_DARK":   "#00C853",   # Koyu yeşil (chat bubble border)

    # -----------------------------------------------------------
    # DANGER (Satış / Negatif)
    # -----------------------------------------------------------
    "COLOR_DANGER":         "#ef4444",   # Kırmızı (Sat butonu, zarar)
    "COLOR_DANGER_HOVER":   "#dc2626",   # Hover
    "COLOR_DANGER_DARK":    "#D50000",   # Koyu kırmızı (sinyal)

    # -----------------------------------------------------------
    # WARNING
    # -----------------------------------------------------------
    "COLOR_WARNING":        "#ca8a04",   # Sarı uyarı (banner arka planı)
    "COLOR_WARNING_DARK":   "#FFD600",   # Parlak sarı (HOLD sinyali)

    # -----------------------------------------------------------
    # PURPLE (AI özellikleri)
    # -----------------------------------------------------------
    "COLOR_PURPLE":         "#8b5cf6",   # Mor buton / ankete katılım
    "COLOR_PURPLE_HOVER":   "#7c3aed",   # Hover
    "COLOR_PURPLE_BRIGHT":  "#a855f7",   # Parlak mor (system chat)

    # -----------------------------------------------------------
    # INDIGO (AI Chatbot gönder)
    # -----------------------------------------------------------
    "COLOR_INDIGO":         "#6366f1",   # Indigo (AI aksiyon butonu)
    "COLOR_INDIGO_HOVER":   "#818cf8",   # Hover

    # -----------------------------------------------------------
    # CHAT BUBBLE BACKGROUNDS
    # -----------------------------------------------------------
    "COLOR_BUBBLE_USER":    "#2A3F5F",   # Kullanıcı mesaj balonu
    "COLOR_BUBBLE_AI":      "#1E2A3A",   # AI mesaj balonu
    "COLOR_BUBBLE_SYSTEM":  "#2D1F3D",   # Sistem mesaj balonu

    # -----------------------------------------------------------
    # FONT SIZES — Okunabilirlik için optimize edilmiş
    # -----------------------------------------------------------
    "FONT_XS":   "11px",   # Zaman damgaları, çok küçük metinler
    "FONT_SM":   "12px",   # Üst yazılar, tablo başlıkları
    "FONT_BASE": "14px",   # Standart gövde metni
    "FONT_MD":   "15px",   # Form elemanları, buton metni
    "FONT_LG":   "16px",   # Büyük etiketler
    "FONT_XL":   "17px",   # Büyük input alanları, fiyat göstergeleri
    "FONT_2XL":  "20px",   # Kart başlık değerleri
    "FONT_3XL":  "22px",   # Sayfa alt başlıkları
    "FONT_4XL":  "26px",   # Sinyal etiketi
    "FONT_5XL":  "30px",   # Büyük fiyat göstergesi
    # Tablo okunabilirliği için özel tokenlar
    "FONT_TABLE_HEADER": "13px",   # Kolon başlıkları (QHeaderView)
    "FONT_TABLE_CELL":   "14px",   # Satır içerikleri

    # -----------------------------------------------------------
    # SPACING (Padding / Margin)
    # -----------------------------------------------------------
    "SPACE_XS":  "4px",
    "SPACE_SM":  "6px",
    "SPACE_MD":  "8px",
    "SPACE_LG":  "10px",
    "SPACE_XL":  "12px",
    "SPACE_2XL": "15px",
    "SPACE_3XL": "20px",
    "SPACE_4XL": "25px",

    # -----------------------------------------------------------
    # BORDER RADIUS
    # -----------------------------------------------------------
    "RADIUS_SM":  "4px",
    "RADIUS_MD":  "6px",
    "RADIUS_LG":  "8px",
    "RADIUS_XL":  "10px",
    "RADIUS_2XL": "12px",
    "RADIUS_FULL": "9999px",  # Tam yuvarlak (pill shape)
}

# Varsayılan tema
DEFAULT_THEME = DARK_THEME
