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
    "COLOR_SIDEBAR":        "#020617",   # Daha koyu sidebar rengi
    "COLOR_BG_ELEVATED":    "#334155",   # Hover, seçili satır (en üst katman)
    "COLOR_BG_OVERLAY":     "#475569",   # Tooltip, dropdown overlay
    "COLOR_CARD_SURFACE":   "#111827",   # Modern kart zemini
    "COLOR_CARD_SURFACE_ALT": "#172033", # Kart gradient ikinci katmani
    "COLOR_CARD_GRADIENT_TOTAL": "#1a2744",
    "COLOR_CARD_GRADIENT_COST": "#271f42",
    "COLOR_CARD_GRADIENT_CAPITAL": "#123226",
    "COLOR_CARD_GRADIENT_RETURNS": "#342814",
    "CARD_TOTAL_ACCENT": "#3b82f6",
    "CARD_TOTAL_BORDER": "rgba(59, 130, 246, 0.42)",
    "CARD_COST_ACCENT": "#8b5cf6",
    "CARD_COST_BORDER": "rgba(139, 92, 246, 0.42)",
    "CARD_CAPITAL_ACCENT": "#10b981",
    "CARD_CAPITAL_BORDER": "rgba(16, 185, 129, 0.42)",
    "CARD_RETURNS_ACCENT": "#f59e0b",
    "CARD_RETURNS_BORDER": "rgba(245, 158, 11, 0.42)",
    "COLOR_SIDEBAR_ACTIVE_BG": "rgba(59, 130, 246, 0.16)",
    "COLOR_SIDEBAR_HOVER_BG": "rgba(255, 255, 255, 0.07)",
    "COLOR_TABLE_POSITIVE_BG": "rgba(16, 185, 129, 0.08)",
    "COLOR_TABLE_NEGATIVE_BG": "rgba(239, 68, 68, 0.08)",
    "COLOR_TABLE_SELECTED_BG": "rgba(59, 130, 246, 0.15)",
    "COLOR_SHADOW":        "#000000",
    "BUTTON_PRIMARY_BG": "#2563eb",
    "BUTTON_PRIMARY_BG_HOVER": "#1d4ed8",
    "BUTTON_PRIMARY_BG_PRESSED": "#1e40af",
    "BUTTON_PRIMARY_TEXT": "#ffffff",
    "BUTTON_SECONDARY_BG": "#111827",
    "BUTTON_SECONDARY_BG_HOVER": "#1f2b3e",
    "BUTTON_SECONDARY_BG_PRESSED": "#334155",
    "BUTTON_SECONDARY_TEXT": "#f1f5f9",
    "BUTTON_SECONDARY_BORDER": "#334155",
    "BUTTON_SECONDARY_BORDER_HOVER": "#475569",
    "BUTTON_DISABLED_BG": "#0f172a",
    "BUTTON_DISABLED_TEXT": "#64748b",
    "BUTTON_DISABLED_BORDER": "#1e293b",
    "BUTTON_DANGER_BG": "#ef4444",
    "BUTTON_DANGER_BG_HOVER": "#dc2626",
    "BUTTON_DANGER_TEXT": "#ffffff",
    "BUTTON_OUTLINE_BG": "transparent",
    "BUTTON_OUTLINE_BG_HOVER": "#1f2b3e",
    "BUTTON_OUTLINE_TEXT": "#f1f5f9",
    "BUTTON_OUTLINE_BORDER": "#475569",
    "NAV_BG": "#020617",
    "NAV_TEXT": "#94a3b8",
    "NAV_TEXT_ACTIVE": "#ffffff",
    "NAV_ACTIVE_BG": "rgba(59, 130, 246, 0.16)",
    "NAV_HOVER_BG": "rgba(255, 255, 255, 0.07)",
    "NAV_BORDER": "rgba(255, 255, 255, 0.08)",
    "CARD_BG": "#111827",
    "CARD_BG_ALT": "#172033",
    "CARD_BORDER": "#1e293b",
    "TABLE_BG": "#111827",
    "TABLE_ALT_BG": "#0f172a",
    "TABLE_HEADER_BG": "#111827",
    "TABLE_TEXT": "#cbd5e1",
    "TABLE_HEADER_TEXT": "#f1f5f9",
    "TABLE_BORDER": "#334155",
    "TABLE_BORDER_SUBTLE": "#1e293b",
    "TABLE_SELECTION_BG": "rgba(59, 130, 246, 0.18)",
    "FORM_BG": "#111827",
    "FORM_BG_FOCUS": "#0f172a",
    "FORM_TEXT": "#f1f5f9",
    "FORM_BORDER": "#334155",
    "FORM_BORDER_FOCUS": "#3b82f6",
    "FORM_LABEL_TEXT": "#cbd5e1",
    "TEXT_LINK": "#38bdf8",
    "TEXT_LINK_HOVER": "#7dd3fc",

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
    "RADIUS_CARD": "14px",
    "RADIUS_FULL": "9999px",  # Tam yuvarlak (pill shape)

    # -----------------------------------------------------------
    # TOOLTIP
    # -----------------------------------------------------------
    "TOOLTIP_BG":     "#1e293b",
    "TOOLTIP_TEXT":   "#e2e8f0",
    "TOOLTIP_BORDER": "#334155",

    # -----------------------------------------------------------
    # SLIDER
    # -----------------------------------------------------------
    "SLIDER_GROOVE_BG":     "#334155",
    "SLIDER_GROOVE_HEIGHT": "4px",
    "SLIDER_HANDLE_BG":     "#3b82f6",
    "SLIDER_HANDLE_BORDER": "#2563eb",
    "SLIDER_HANDLE_SIZE":   "14px",

    # -----------------------------------------------------------
    # TOAST / FEEDBACK
    # -----------------------------------------------------------
    "TOAST_SUCCESS_BG":     "#14532d",
    "TOAST_SUCCESS_BORDER": "#10b981",
    "TOAST_WARNING_BG":     "#78350f",
    "TOAST_WARNING_BORDER": "#ca8a04",
    "TOAST_ERROR_BG":       "#7f1d1d",
    "TOAST_ERROR_BORDER":   "#ef4444",
    "TOAST_INFO_BG":        "#1e3a5f",
    "TOAST_INFO_BORDER":    "#3b82f6",
    "TOAST_TEXT":           "#f1f5f9",

    # -----------------------------------------------------------
    # PROGRESS BAR (semantic)
    # -----------------------------------------------------------
    "PROGRESS_DEFAULT_BG":  "#3b82f6",
    "PROGRESS_SUCCESS_BG":  "#10b981",
    "PROGRESS_DANGER_BG":   "#ef4444",
    "PROGRESS_WARNING_BG":  "#ca8a04",
    "PROGRESS_TRACK_BG":    "#334155",
    "PROGRESS_BORDER_RADIUS": "4px",

    # -----------------------------------------------------------
    # SPLITTER
    # -----------------------------------------------------------
    "SPLITTER_HANDLE_BG":    "#334155",
    "SPLITTER_HANDLE_HOVER": "#3b82f6",
    "SPLITTER_HANDLE_WIDTH": "3px",

    # -----------------------------------------------------------
    # MENU / MENUBAR
    # -----------------------------------------------------------
    "MENU_BG":            "#1e293b",
    "MENU_ITEM_HOVER_BG": "#334155",
    "MENU_SEPARATOR":     "#1e293b",
    "MENU_TEXT":          "#f1f5f9",
    "MENU_SHORTCUT_TEXT": "#64748b",

    # -----------------------------------------------------------
    # INPUT — Semantic States
    # -----------------------------------------------------------
    "INPUT_ERROR_BORDER":       "#ef4444",
    "INPUT_SUCCESS_BORDER":     "#10b981",
    "INPUT_WARNING_BORDER":     "#ca8a04",
    "INPUT_PLACEHOLDER_COLOR":  "#64748b",

    # -----------------------------------------------------------
    # BADGE
    # -----------------------------------------------------------
    "BADGE_SUCCESS_BG":   "#14532d",
    "BADGE_SUCCESS_TEXT": "#22c55e",
    "BADGE_DANGER_BG":    "#7f1d1d",
    "BADGE_DANGER_TEXT":  "#ef4444",
    "BADGE_WARNING_BG":   "#78350f",
    "BADGE_WARNING_TEXT": "#fbbf24",
    "BADGE_INFO_BG":      "#1e3a5f",
    "BADGE_INFO_TEXT":    "#60a5fa",
    "BADGE_NEUTRAL_BG":   "#334155",
    "BADGE_NEUTRAL_TEXT": "#94a3b8",

    # -----------------------------------------------------------
    # TREE WIDGET
    # -----------------------------------------------------------
    "TREE_BG":          "#111827",
    "TREE_ALT_BG":      "#0f172a",
    "TREE_HEADER_BG":   "#111827",
    "TREE_TEXT":        "#cbd5e1",
    "TREE_HEADER_TEXT": "#f1f5f9",
    "TREE_BORDER":      "#334155",
    "TREE_SELECTION_BG": "rgba(59, 130, 246, 0.18)",
}


# ============================================================
#  LIGHT THEME TOKENS
#  DARK_THEME üzerinden sadece görsel tokenlar override edilir.
# ============================================================
LIGHT_THEME: dict[str, str] = {
    **DARK_THEME,   # Font, spacing, radius ve brand renkleri miras alınır

    # -----------------------------------------------------------
    # BACKGROUND (Açık Arka Plan Katmanları)
    # -----------------------------------------------------------
    "COLOR_BG_BASE":        "#f1f5f9",   # Açık mavi-gri sayfa zemini
    "COLOR_BG_SURFACE":     "#ffffff",   # Beyaz kartlar / paneller
    "COLOR_SIDEBAR":        "#1e293b",   # Sidebar her iki temada da koyu kalır
    "COLOR_BG_ELEVATED":    "#e2e8f0",   # Hover / seçili satır
    "COLOR_BG_OVERLAY":     "#cbd5e1",   # Tooltip / dropdown
    "COLOR_CARD_SURFACE":   "#ffffff",
    "COLOR_CARD_SURFACE_ALT": "#eef4ff",
    "COLOR_CARD_GRADIENT_TOTAL": "#dceafe",
    "COLOR_CARD_GRADIENT_COST": "#ede9fe",
    "COLOR_CARD_GRADIENT_CAPITAL": "#dcfce7",
    "COLOR_CARD_GRADIENT_RETURNS": "#ffedd5",
    "CARD_TOTAL_ACCENT": "#2563eb",
    "CARD_TOTAL_BORDER": "#93c5fd",
    "CARD_COST_ACCENT": "#7c3aed",
    "CARD_COST_BORDER": "#c4b5fd",
    "CARD_CAPITAL_ACCENT": "#059669",
    "CARD_CAPITAL_BORDER": "#86efac",
    "CARD_RETURNS_ACCENT": "#d97706",
    "CARD_RETURNS_BORDER": "#fbbf24",
    "COLOR_SIDEBAR_ACTIVE_BG": "rgba(59, 130, 246, 0.20)",
    "COLOR_SIDEBAR_HOVER_BG": "rgba(255, 255, 255, 0.08)",
    "COLOR_TABLE_POSITIVE_BG": "rgba(16, 185, 129, 0.10)",
    "COLOR_TABLE_NEGATIVE_BG": "rgba(239, 68, 68, 0.10)",
    "COLOR_TABLE_SELECTED_BG": "rgba(59, 130, 246, 0.15)",
    "COLOR_SHADOW":        "#0f172a",
    "BUTTON_PRIMARY_BG": "#2563eb",
    "BUTTON_PRIMARY_BG_HOVER": "#1d4ed8",
    "BUTTON_PRIMARY_BG_PRESSED": "#1e40af",
    "BUTTON_PRIMARY_TEXT": "#ffffff",
    "BUTTON_SECONDARY_BG": "#f8fbff",
    "BUTTON_SECONDARY_BG_HOVER": "#eef4ff",
    "BUTTON_SECONDARY_BG_PRESSED": "#e2e8f0",
    "BUTTON_SECONDARY_TEXT": "#0f172a",
    "BUTTON_SECONDARY_BORDER": "#b6c6d9",
    "BUTTON_SECONDARY_BORDER_HOVER": "#2563eb",
    "BUTTON_DISABLED_BG": "#f1f5f9",
    "BUTTON_DISABLED_TEXT": "#94a3b8",
    "BUTTON_DISABLED_BORDER": "#e2e8f0",
    "BUTTON_DANGER_BG": "#dc2626",
    "BUTTON_DANGER_BG_HOVER": "#b91c1c",
    "BUTTON_DANGER_TEXT": "#ffffff",
    "BUTTON_OUTLINE_BG": "transparent",
    "BUTTON_OUTLINE_BG_HOVER": "#f8fafc",
    "BUTTON_OUTLINE_TEXT": "#0f172a",
    "BUTTON_OUTLINE_BORDER": "#cbd5e1",
    "NAV_BG": "#1e293b",
    "NAV_TEXT": "#cbd5e1",
    "NAV_TEXT_ACTIVE": "#ffffff",
    "NAV_ACTIVE_BG": "rgba(59, 130, 246, 0.20)",
    "NAV_HOVER_BG": "rgba(255, 255, 255, 0.08)",
    "NAV_BORDER": "rgba(255, 255, 255, 0.10)",
    "CARD_BG": "#ffffff",
    "CARD_BG_ALT": "#eef4ff",
    "CARD_BORDER": "#dbe3ef",
    "TABLE_BG": "#ffffff",
    "TABLE_ALT_BG": "#f1f5f9",
    "TABLE_HEADER_BG": "#ffffff",
    "TABLE_TEXT": "#0f172a",
    "TABLE_HEADER_TEXT": "#020617",
    "TABLE_BORDER": "#cbd5e1",
    "TABLE_BORDER_SUBTLE": "#e2e8f0",
    "TABLE_SELECTION_BG": "rgba(37, 99, 235, 0.16)",
    "FORM_BG": "#ffffff",
    "FORM_BG_FOCUS": "#ffffff",
    "FORM_TEXT": "#0f172a",
    "FORM_BORDER": "#cbd5e1",
    "FORM_BORDER_FOCUS": "#2563eb",
    "FORM_LABEL_TEXT": "#334155",
    "TEXT_LINK": "#0369a1",
    "TEXT_LINK_HOVER": "#075985",

    # -----------------------------------------------------------
    # BORDERS
    # -----------------------------------------------------------
    "COLOR_BORDER":         "#e2e8f0",
    "COLOR_BORDER_SUBTLE":  "#f1f5f9",

    # -----------------------------------------------------------
    # TEXT (İçerik alanı — beyaz arka plan üzeri)
    # -----------------------------------------------------------
    "COLOR_TEXT_PRIMARY":   "#0f172a",   # Koyu başlık metni
    "COLOR_TEXT_SECONDARY": "#64748b",   # İkincil metin
    "COLOR_TEXT_MUTED":     "#94a3b8",   # Soluk metin
    "COLOR_TEXT_BODY":      "#334155",   # Gövde metni
    "COLOR_TEXT_BRIGHT":    "#020617",   # En koyu (vurgulu metin)

    # -----------------------------------------------------------
    # ACCENT (Açık arka planda biraz daha koyu cyan)
    # -----------------------------------------------------------
    "COLOR_ACCENT":         "#0284c7",
    "COLOR_ACCENT_HOVER":   "#0369a1",
    "COLOR_ACCENT_LIGHT":   "#38bdf8",

    # -----------------------------------------------------------
    # CHAT BUBBLE BACKGROUNDS (Açık tema için pastel tonlar)
    # -----------------------------------------------------------
    "COLOR_BUBBLE_USER":    "#dbeafe",
    "COLOR_BUBBLE_AI":      "#f0f9ff",
    "COLOR_BUBBLE_SYSTEM":  "#f5f3ff",

    # -----------------------------------------------------------
    # TOOLTIP
    # -----------------------------------------------------------
    "TOOLTIP_BG":     "#ffffff",
    "TOOLTIP_TEXT":   "#0f172a",
    "TOOLTIP_BORDER": "#e2e8f0",

    # -----------------------------------------------------------
    # SLIDER
    # -----------------------------------------------------------
    "SLIDER_GROOVE_BG":     "#e2e8f0",
    "SLIDER_HANDLE_BG":     "#2563eb",
    "SLIDER_HANDLE_BORDER": "#1d4ed8",

    # -----------------------------------------------------------
    # TOAST / FEEDBACK
    # -----------------------------------------------------------
    "TOAST_SUCCESS_BG":     "#f0fdf4",
    "TOAST_SUCCESS_BORDER": "#059669",
    "TOAST_WARNING_BG":     "#fffbeb",
    "TOAST_WARNING_BORDER": "#d97706",
    "TOAST_ERROR_BG":       "#fef2f2",
    "TOAST_ERROR_BORDER":   "#dc2626",
    "TOAST_INFO_BG":        "#eff6ff",
    "TOAST_INFO_BORDER":    "#2563eb",
    "TOAST_TEXT":           "#0f172a",

    # -----------------------------------------------------------
    # PROGRESS BAR
    # -----------------------------------------------------------
    "PROGRESS_TRACK_BG":    "#e2e8f0",

    # -----------------------------------------------------------
    # SPLITTER
    # -----------------------------------------------------------
    "SPLITTER_HANDLE_BG":    "#e2e8f0",
    "SPLITTER_HANDLE_HOVER": "#2563eb",

    # -----------------------------------------------------------
    # MENU
    # -----------------------------------------------------------
    "MENU_BG":            "#ffffff",
    "MENU_ITEM_HOVER_BG": "#f1f5f9",
    "MENU_SEPARATOR":     "#e2e8f0",
    "MENU_TEXT":          "#0f172a",
    "MENU_SHORTCUT_TEXT": "#64748b",

    # -----------------------------------------------------------
    # INPUT — Semantic States
    # -----------------------------------------------------------
    "INPUT_ERROR_BORDER":      "#dc2626",
    "INPUT_SUCCESS_BORDER":    "#059669",
    "INPUT_WARNING_BORDER":    "#d97706",
    "INPUT_PLACEHOLDER_COLOR": "#94a3b8",

    # -----------------------------------------------------------
    # BADGE
    # -----------------------------------------------------------
    "BADGE_SUCCESS_BG":   "#f0fdf4",
    "BADGE_SUCCESS_TEXT": "#059669",
    "BADGE_DANGER_BG":    "#fef2f2",
    "BADGE_DANGER_TEXT":  "#dc2626",
    "BADGE_WARNING_BG":   "#fffbeb",
    "BADGE_WARNING_TEXT": "#d97706",
    "BADGE_INFO_BG":      "#eff6ff",
    "BADGE_INFO_TEXT":    "#2563eb",
    "BADGE_NEUTRAL_BG":   "#f1f5f9",
    "BADGE_NEUTRAL_TEXT": "#64748b",

    # -----------------------------------------------------------
    # TREE WIDGET
    # -----------------------------------------------------------
    "TREE_BG":           "#ffffff",
    "TREE_ALT_BG":       "#f1f5f9",
    "TREE_HEADER_BG":    "#f8fafc",
    "TREE_TEXT":         "#0f172a",
    "TREE_HEADER_TEXT":  "#020617",
    "TREE_BORDER":       "#e2e8f0",
    "TREE_SELECTION_BG": "rgba(37, 99, 235, 0.16)",
}

# Sidebar nav butonlarının hover rengi — sidebar her zaman koyu kaldığından
# her iki temada da açık metin rengi kullanılır.
DARK_THEME["COLOR_NAV_TEXT_ACTIVE"]  = "#f1f5f9"
LIGHT_THEME["COLOR_NAV_TEXT_ACTIVE"] = "#f8fafc"

# Varsayılan tema (ThemeManager runtime'da günceller)
DEFAULT_THEME = DARK_THEME
