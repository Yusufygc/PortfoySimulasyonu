pragma Singleton
import QtQuick

QtObject {
    id: root

    // --- Uygulama Başlıkları ---
    readonly property string appName: "PORTFÖY SİMÜLASYONU"
    readonly property string windowTitle: "Portföy Simülasyonu - Modern QML & TradingView"

    // --- Navigasyon Başlıkları ---
    readonly property string navCollapse: "Menüyü Daralt"
    readonly property string navExpand: "Menüyü Genişlet"
    readonly property string navDashboard: "Genel Bakış"
    readonly property string navWatchlist: "İzleme Listeleri"
    readonly property string navPortfolio: "Model Portföyler"
    readonly property string navStock360: "Hisse 360"
    readonly property string navCompare: "Karşılaştırma Lab"
    readonly property string navScreener: "Hisse Tarayıcı"
    readonly property string navPlanning: "Finansal Planlama"
    readonly property string navOptimization: "Optimizasyon"
    readonly property string navAI: "AI Asistan"
    readonly property string navSettings: "Ayarlar"

    // --- Üst Bar (Header) ---
    readonly property string searchPlaceholder: "Hisse Ara (örn. THYAO)..."
    readonly property string marketOpen: "BIST: Canlı Seans Açık"
    readonly property string marketClosed: "BIST: Seans Kapalı"

    // --- Dashboard Görünümü ---
    readonly property string dashboardTitle: "Portföy Genel Bakış"
    readonly property string dashboardSubtitle: "Gerçek zamanlı piyasa değerlemeleri, canlı emirler ve varlık dağılımı"
    readonly property string btnRefresh: "Fiyatları Yenile"
    readonly property string btnRefreshing: "Yenileniyor..."
    readonly property string btnCapital: "Sermaye Yönetimi"
    readonly property string btnQuickTrade: "+ Hızlı Alım / Satım"

    // --- KPI Kartları ---
    readonly property string kpiTotalValue: "Toplam Portföy Değeri"
    readonly property string kpiDailyGainLoss: "Günlük Kâr / Zarar"
    readonly property string kpiUnrealizedPL: "Toplam Gerçekleşmemiş K/Z"
    readonly property string kpiCashRatio: "Nakit Bakiye & Oran"
    readonly property string kpiDailyChange: "Günlük Değişim"
    readonly property string kpiTodayReturn: "Bugünkü Getiri"
    readonly property string kpiCostPrefix: "Maliyet: "
    readonly property string kpiOpenPositionsSuffix: " Açık Pozisyon"

    // --- TradingView Araç Çubuğu & Grafikler ---
    readonly property string tvChartTitle: "TRADINGVIEW CANLI GRAFİK"
    readonly property string tvPortfolioHoldings: "PORTFÖY HİSSELERİ:"
    readonly property string btnIndicators: "İndikatörler"
    readonly property string tooltipFit: "Grafiği Ekrana Sığdır"
    readonly property string tooltipFullscreen: "Tam Ekran Laboratuvarı"
    readonly property string closeFullscreen: "Kapat"
    readonly property string technicalIndicators: "TEKNİK İNDİKATÖRLER"

    // Zaman Dilimleri
    readonly property string tf1D: "1G"
    readonly property string tf1W: "1H"
    readonly property string tf1M: "1A"

    // Grafik Türleri
    readonly property string chartCandle: "Mum"
    readonly property string chartLine: "Çizgi"
    readonly property string chartArea: "Alan"
    readonly property string chartBar: "Bar"

    // --- Tablo & Pozisyonlar ---
    readonly property string positionsTableTitle: "Açık Pozisyonlar ve Canlı Değerleme"
    readonly property string positionsTableSubtitle: "Fiyatlar değiştikçe yeşil/kırmızı yanıp söner • Satıra tıklayarak grafiğini açabilirsiniz"
    readonly property string thSymbolCompany: "SEMBOL & ŞİRKET"
    readonly property string thQuantity: "LOT"
    readonly property string thAvgCost: "MALİYET"
    readonly property string thLastPrice: "SON FİYAT"
    readonly property string thDailyChange: "GÜNLÜK %"
    readonly property string thMarketValue: "PİYASA DEĞERİ"
    readonly property string thPLTRY: "K/Z (₺)"
    readonly property string thPLPct: "K/Z %"
    readonly property string thWeight: "AĞIRLIK"
    readonly property string thActions: "İŞLEMLER"
    readonly property string btnChart: "Grafik"
    readonly property string btnTrade: "İşlem"

    // --- Varlık Dağılımı (Allocation) ---
    readonly property string allocationTitle: "Varlık Dağılımı (Allocation)"
    readonly property string allocationShare: "Hisse Payı"
    readonly property string portfolioBalanceStatus: "Portföy Denge Durumu"
    readonly property string portfolioBalanceGood: "Hisse ağırlığı hedef sınırda (%65-70). Nakit rezervi acil alımlar için yeterli."

    // --- Modallar ---
    readonly property string modalTradeTitle: "Hisse Alım / Satım Emri"
    readonly property string modalCapitalTitle: "Sermaye Yönetimi (Nakit Akışı)"
    readonly property string labelStock: "Hisse Sembolü"
    readonly property string labelPrice: "İşlem Fiyatı (₺)"
    readonly property string labelLot: "Lot Adedi"
    readonly property string labelTotalAmount: "Toplam Tutar:"
    readonly property string btnBuy: "AL"
    readonly property string btnSell: "SAT"
    readonly property string btnBuyOrder: "HİSSE AL (BUY)"
    readonly property string btnSellOrder: "HİSSE SAT (SELL)"
    readonly property string btnBuyConfirm: "Alım Emrini Onayla"
    readonly property string btnSellConfirm: "Satış Emrini Onayla"
    readonly property string btnDeposit: "Nakit Yatır"
    readonly property string btnWithdraw: "Nakit Çek"
    readonly property string btnDepositCapital: "Sermaye Yatır"
    readonly property string btnWithdrawCash: "Nakit Çek"
    readonly property string btnExecute: "Emri Onayla"
    readonly property string btnCancel: "İptal"
    readonly property string btnBackToDashboard: "Dashboard'a Dön"

    // --- İzleme Listeleri (Watchlist - Faz 4) ---
    readonly property string watchlistTitle: "İzleme Listelerim (Watchlist)"
    readonly property string watchlistSubtitle: "Kişiselleştirilmiş hisse takip portföyleri, canlı fiyat hareketleri ve mini trend analizleri"
    readonly property string btnNewWatchlist: "+ Yeni Liste"
    readonly property string btnAddStockToWatchlist: "+ Hisse Ekle"
    readonly property string btnEditWatchlist: "Listeyi Düzenle"
    readonly property string btnDeleteWatchlist: "Listeyi Sil"
    readonly property string watchlistMyLists: "TAKİP LİSTELERİM"
    readonly property string thDayRange: "GÜN ARALIĞI (D-Y)"
    readonly property string thTrend7D: "7G TREND"
    readonly property string thNotes: "NOTLAR & STRATEJİ"
    readonly property string modalNewWatchlistTitle: "Yeni Takip Listesi Oluştur"
    readonly property string modalEditWatchlistTitle: "Takip Listesini Düzenle"
    readonly property string modalAddStockTitle: "Listeye Hisse Ekle"
    readonly property string modalEditNoteTitle: "Hisse Notunu Düzenle"
    readonly property string labelListName: "Liste Adı"
    readonly property string labelListDesc: "Açıklama (Opsiyonel)"
    readonly property string labelStockNotes: "Hisseye Dair Notunuz (Strateji / Hedef Fiyat)"
    readonly property string emptyWatchlistTitle: "Bu listede henüz hisse bulunmuyor"
    readonly property string emptyWatchlistSubtitle: "Yukarıdaki '+ Hisse Ekle' butonuna tıklayarak istediğiniz BIST hissesini listenize ekleyebilirsiniz."
    readonly property string kpiActiveList: "Aktif Liste"
    readonly property string kpiGainersLosers: "Yükselen / Düşen"
    readonly property string kpiAvgChange: "Ortalama Değişim"
    readonly property string btnSave: "Kaydet"
}
