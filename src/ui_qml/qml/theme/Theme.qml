pragma Singleton
import QtQuick

QtObject {
    id: root

    property bool isDark: true

    // --- Arka Plan Renkleri ---
    readonly property color bgPrimary: isDark ? "#131722" : "#f8f9fd"
    readonly property color bgSecondary: isDark ? "#1e222d" : "#ffffff"
    readonly property color bgCard: isDark ? "#242731" : "#ffffff"
    readonly property color bgCardHover: isDark ? "#2a2e39" : "#f0f3fa"
    readonly property color bgSidebar: isDark ? "#181b24" : "#f1f3f8"
    readonly property color bgTitlebar: isDark ? "#131722" : "#f8f9fd"
    readonly property color bgInput: isDark ? "#1a1e29" : "#f0f2f7"

    // --- Sınır / Çerçeve Çizgileri ---
    readonly property color borderSubtle: isDark ? "#2a2e39" : "#e0e3eb"
    readonly property color borderCard: isDark ? "#2d313d" : "#e8ecf4"
    readonly property color borderStrong: isDark ? "#434958" : "#c2c8d4"
    readonly property color borderFocus: "#2962ff"

    // --- Metin Renkleri ---
    readonly property color textPrimary: isDark ? "#e0e3eb" : "#131722"
    readonly property color textSecondary: isDark ? "#9db2ce" : "#606775"
    readonly property color textMuted: isDark ? "#637085" : "#959da8"
    readonly property color textInverse: isDark ? "#131722" : "#ffffff"

    // --- Finansal & Vurgu Renkleri (TradingView Standartı) ---
    readonly property color bullGreen: "#089981"
    readonly property color bullGreenSoft: isDark ? "#103932" : "#e0f6f0"
    readonly property color bearRed: "#f23645"
    readonly property color bearRedSoft: isDark ? "#401d24" : "#feebee"
    readonly property color accent: "#2962ff"
    readonly property color accentHover: "#1e53e5"
    readonly property color accentSoft: isDark ? "#1b294d" : "#e8efff"
    readonly property color warningYellow: "#ff9800"
    readonly property color warningYellowSoft: isDark ? "#3e2710" : "#fff8e1"

    // --- Semantik Renkler (Kolay ve standart erişim için) ---
    readonly property color success: bullGreen
    readonly property color successSoft: bullGreenSoft
    readonly property color danger: bearRed
    readonly property color dangerSoft: bearRedSoft
    readonly property color warning: warningYellow
    readonly property color warningSoft: warningYellowSoft
    readonly property color info: accent
    readonly property color infoSoft: accentSoft

    // --- Scrollbar Renkleri (Modern TradingView Tarzı) ---
    readonly property color scrollbarThumb: isDark ? "#363a45" : "#c2c8d4"
    readonly property color scrollbarThumbHover: isDark ? "#505666" : "#8c94a6"
    readonly property color scrollbarThumbActive: accent

    // --- Boyutlar & Boşluklar ---
    readonly property int spaceXs: 4
    readonly property int spaceSm: 8
    readonly property int spaceMd: 16
    readonly property int spaceLg: 24
    readonly property int spaceXl: 32

    // --- Köşe Yuvarlama (Radius) ---
    readonly property int radiusXs: 4
    readonly property int radiusSm: 6
    readonly property int radiusMd: 10
    readonly property int radiusLg: 14
    readonly property int radiusFull: 9999

    // --- Font Boyutları ---
    readonly property int fontXs: 10
    readonly property int fontSm: 12
    readonly property int fontBase: 13
    readonly property int fontMd: 15
    readonly property int fontLg: 18
    readonly property int fontXl: 22
    readonly property int font2Xl: 28

    // --- Font Ailesi ---
    readonly property string fontFamily: "Segoe UI, -apple-system, BlinkMacSystemFont, Roboto, sans-serif"
    readonly property string monoFontFamily: "'Segoe UI', 'Cascadia Code', Consolas, monospace"
    readonly property string fontMono: monoFontFamily
}

