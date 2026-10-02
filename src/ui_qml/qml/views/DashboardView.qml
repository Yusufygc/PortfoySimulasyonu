import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    id: root

    ScrollView {
        id: mainScrollView
        anchors.fill: parent
        clip: true
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

        ScrollBar.vertical: ModernScrollBar {
            parent: mainScrollView
            x: mainScrollView.mirrored ? 2 : mainScrollView.width - width - 3
            y: mainScrollView.topPadding + 2
            height: mainScrollView.availableHeight - 4
            active: mainScrollView.ScrollBar.vertical.active
        }

        ColumnLayout {
            width: mainScrollView.availableWidth
            spacing: Theme.spaceMd

            // Üst Başlık ve Aksiyon Butonları (dar pencerede butonlar başlığın altına geçer)
            GridLayout {
                Layout.fillWidth: true
                columns: root.width < 1060 ? 1 : 2
                columnSpacing: Theme.spaceMd
                rowSpacing: Theme.spaceSm

                Column {
                    spacing: 2
                    Text {
                        text: Strings.dashboardTitle
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXl
                        font.weight: Font.Bold
                        color: Theme.textPrimary
                    }
                    Text {
                        text: Strings.dashboardSubtitle
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        color: Theme.textMuted
                    }
                    Text {
                        visible: dashboardController.lastUpdateText !== ""
                        text: dashboardController.lastUpdateText
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        color: Theme.textMuted
                    }
                }

                Flow {
                    Layout.alignment: root.width < 1060 ? Qt.AlignLeft : Qt.AlignRight
                    Layout.fillWidth: root.width < 1060
                    spacing: Theme.spaceSm

                // Canlı Fiyat Yenile Butonu (Yükleniyor animasyonu ile)
                ModernButton {
                    text: dashboardController.isRefreshing ? Strings.btnRefreshing : Strings.btnRefresh
                    iconName: "refresh"
                    variant: "secondary"
                    enabled: !dashboardController.isRefreshing
                    onClicked: {
                        dashboardController.refreshMetrics()
                        chartView.loadStock(chartView.ticker)
                    }
                }

                // Kapanış Fiyatlarını Güncelle (tarihsel veri + getiriler)
                ModernButton {
                    text: dashboardController.isUpdatingPrices ? Strings.btnUpdatingClosingPrices : Strings.btnUpdateClosingPrices
                    iconName: "history"
                    variant: "secondary"
                    enabled: !dashboardController.isUpdatingPrices
                    onClicked: dashboardController.updateClosingPrices()
                }

                // Sermaye Yönetimi Butonu
                ModernButton {
                    text: Strings.btnCapital
                    iconName: "capital"
                    variant: "secondary"
                    onClicked: capitalModal.open()
                }

                // Excel Raporu Butonu
                ModernButton {
                    text: Strings.btnExportExcel
                    iconName: "filetext"
                    variant: "secondary"
                    onClicked: {
                        if (typeof dashboardController !== "undefined") {
                            excelDialog.open(dashboardController.firstTradeDateText(), "Portfoy_Raporu.xlsx")
                        }
                    }
                }

                // Hızlı Al/Sat Butonu
                ModernButton {
                    text: Strings.btnQuickTrade
                    iconName: "zap"
                    variant: "primary"
                    onClicked: tradeModal.open(chartView.ticker, 0)
                }
                }
            }

            // 1. KPI Metrik Kartları (4 Adet; dar pencerede 2x2)
            GridLayout {
                Layout.fillWidth: true
                columns: root.width < 980 ? 2 : 4
                columnSpacing: Theme.spaceMd
                rowSpacing: Theme.spaceMd
                uniformCellWidths: true

                MetricCard {
                    Layout.fillWidth: true
                    title: Strings.kpiTotalValue
                    value: dashboardController.totalValue
                    changeText: dashboardController.dailyGainLossPct
                    isPositive: dashboardController.isDailyPositive
                    subText: Strings.kpiDailyChange
                    iconName: "banknote"
                }

                MetricCard {
                    Layout.fillWidth: true
                    title: Strings.kpiDailyGainLoss
                    value: dashboardController.dailyGainLoss
                    changeText: dashboardController.dailyGainLossPct
                    isPositive: dashboardController.isDailyPositive
                    subText: Strings.kpiTodayReturn
                    iconName: "trendingup"
                }

                MetricCard {
                    Layout.fillWidth: true
                    title: Strings.kpiUnrealizedPL
                    value: dashboardController.totalGainLoss
                    changeText: dashboardController.totalGainLossPct
                    isPositive: dashboardController.isTotalPositive
                    subText: Strings.kpiCostPrefix + dashboardController.totalCost
                    iconName: "linechart"
                }

                MetricCard {
                    Layout.fillWidth: true
                    title: Strings.kpiCashRatio
                    value: dashboardController.cashBalance
                    changeText: dashboardController.cashRatio
                    isPositive: true
                    subText: dashboardController.holdingsCount + Strings.kpiOpenPositionsSuffix
                    iconName: "portfolio"
                }
            }

            // 1b. Dönemsel Getiriler (haftalık / aylık)
            GridLayout {
                Layout.fillWidth: true
                columns: 2
                columnSpacing: Theme.spaceMd
                rowSpacing: Theme.spaceMd
                uniformCellWidths: true

                MetricCard {
                    Layout.fillWidth: true
                    implicitHeight: 96
                    title: Strings.kpiWeeklyReturn
                    value: dashboardController.weeklyReturnText
                    changeText: Strings.kpiWeeklyBadge
                    isPositive: dashboardController.isWeeklyPositive
                    subText: Strings.kpiPeriodReturnSub
                    iconName: "trendingup"
                }

                MetricCard {
                    Layout.fillWidth: true
                    implicitHeight: 96
                    title: Strings.kpiMonthlyReturn
                    value: dashboardController.monthlyReturnText
                    changeText: Strings.kpiMonthlyBadge
                    isPositive: dashboardController.isMonthlyPositive
                    subText: Strings.kpiPeriodReturnSub
                    iconName: "trendingup"
                }
            }

            // 2. Orta Blok: TradingView Grafiği & Portföy Dağılımı Donut
            GridLayout {
                id: midGrid
                readonly property bool stacked: root.width < 1000
                Layout.fillWidth: true
                Layout.preferredHeight: stacked ? 480 + 340 + Theme.spaceMd : 520
                columns: stacked ? 1 : 2
                columnSpacing: Theme.spaceMd
                rowSpacing: Theme.spaceMd

                // Sol: TradingView Mum Grafiği & Teknik Analiz
                ModernCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredHeight: 480

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: Theme.spaceSm
                        spacing: Theme.spaceSm

                        // 1. TradingView Gelişmiş Toolbar (Zaman Dilimleri, Grafik Türleri, İndikatörler)
                        TradingViewToolbar {
                            id: tvToolbar
                            Layout.fillWidth: true
                            chartView: chartView
                            onToggleFullscreen: chartModal.open()
                        }

                        // 2. Hızlı Portföy Hisseleri Seçici Barı (Taşmayı önleyen esnek kaydırma)
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spaceSm

                            Text {
                                text: Strings.tvPortfolioHoldings
                                font.family: Theme.fontFamily
                                font.pixelSize: 10
                                font.weight: Font.Bold
                                color: Theme.textMuted
                                Layout.alignment: Qt.AlignVCenter
                            }

                            Flickable {
                                id: tickersFlickable
                                Layout.fillWidth: true
                                implicitHeight: 26
                                contentWidth: tickersRow.implicitWidth
                                contentHeight: 26
                                clip: true
                                boundsBehavior: Flickable.StopAtBounds

                                Row {
                                    id: tickersRow
                                    spacing: Theme.spaceXs

                                    Repeater {
                                        model: dashboardController ? dashboardController.quickTickers : ["OBAMS", "PSGYO", "BINHO"]
                                        ModernButton {
                                            text: (modelData || "").replace(/\.IS$/i, "")
                                            variant: (chartController && chartController.currentTicker === modelData) ? "primary" : "ghost"
                                            implicitHeight: 24
                                            onClicked: {
                                                chartView.loadStock(modelData)
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        // 3. TradingView QML Bileşeni
                        TradingViewChart {
                            id: chartView
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            ticker: chartController ? (chartController.currentTicker || "").replace(/\.IS$/i, "") : "OBAMS"
                        }
                    }
                }

                // Sağ: Varlık Dağılımı Donut Kartı
                AssetAllocationCard {
                    id: allocationCard
                    Layout.fillWidth: midGrid.stacked
                    Layout.preferredWidth: midGrid.stacked ? -1 : 320
                    Layout.preferredHeight: 340
                    Layout.fillHeight: true
                }
            }

            // 3. Alt Blok: Açık Pozisyonlar Tablosu (Positions Table)
            ModernCard {
                Layout.fillWidth: true
                implicitHeight: tableColumn.implicitHeight + 36

                ColumnLayout {
                    id: tableColumn
                    anchors.fill: parent
                    anchors.margins: Theme.spaceMd
                    spacing: Theme.spaceSm

                    // Tablo Üst Başlık & Özet
                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: Strings.positionsTableTitle
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontMd
                            font.weight: Font.Bold
                            color: Theme.textPrimary
                            Layout.fillWidth: true
                        }
                        Text {
                            text: Strings.positionsTableSubtitle
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            color: Theme.textMuted
                        }
                    }

                    // Tablo: dar pencerede yatay kaydırılır (sütun hizası bozulmaz)
                    Flickable {
                        id: tableFlick
                        Layout.fillWidth: true
                        implicitHeight: tableInner.implicitHeight + 10
                        contentWidth: Math.max(width, 1130)
                        contentHeight: tableInner.implicitHeight
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds
                        ScrollBar.horizontal: ModernScrollBar {}

                        ColumnLayout {
                            id: tableInner
                            width: tableFlick.contentWidth
                            spacing: Theme.spaceSm

                    // Tablo Başlık Satırı
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 34
                        radius: Theme.radiusSm
                        color: Theme.bgInput

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            spacing: 8

                            Text {
                                text: Strings.thSymbolCompany
                                color: Theme.textMuted
                                font.pixelSize: 11
                                font.weight: Font.Bold
                                Layout.fillWidth: true
                                Layout.minimumWidth: 160
                            }
                            Text {
                                text: Strings.thQuantity
                                color: Theme.textMuted
                                font.pixelSize: 11
                                font.weight: Font.Bold
                                Layout.preferredWidth: 70
                                Layout.minimumWidth: 70
                                Layout.maximumWidth: 70
                                horizontalAlignment: Text.AlignRight
                            }
                            Text {
                                text: Strings.thAvgCost
                                color: Theme.textMuted
                                font.pixelSize: 11
                                font.weight: Font.Bold
                                Layout.preferredWidth: 85
                                Layout.minimumWidth: 85
                                Layout.maximumWidth: 85
                                horizontalAlignment: Text.AlignRight
                            }
                            Text {
                                text: Strings.thLastPrice
                                color: Theme.textMuted
                                font.pixelSize: 11
                                font.weight: Font.Bold
                                Layout.preferredWidth: 85
                                Layout.minimumWidth: 85
                                Layout.maximumWidth: 85
                                horizontalAlignment: Text.AlignRight
                            }
                            Text {
                                text: Strings.thDailyChange
                                color: Theme.textMuted
                                font.pixelSize: 11
                                font.weight: Font.Bold
                                Layout.preferredWidth: 75
                                Layout.minimumWidth: 75
                                Layout.maximumWidth: 75
                                horizontalAlignment: Text.AlignRight
                            }
                            Text {
                                text: Strings.thMarketValue
                                color: Theme.textMuted
                                font.pixelSize: 11
                                font.weight: Font.Bold
                                Layout.preferredWidth: 115
                                Layout.minimumWidth: 115
                                Layout.maximumWidth: 115
                                horizontalAlignment: Text.AlignRight
                            }
                            Text {
                                text: Strings.thPLTRY
                                color: Theme.textMuted
                                font.pixelSize: 11
                                font.weight: Font.Bold
                                Layout.preferredWidth: 110
                                Layout.minimumWidth: 110
                                Layout.maximumWidth: 110
                                horizontalAlignment: Text.AlignRight
                            }
                            Text {
                                text: Strings.thPLPct
                                color: Theme.textMuted
                                font.pixelSize: 11
                                font.weight: Font.Bold
                                Layout.preferredWidth: 75
                                Layout.minimumWidth: 75
                                Layout.maximumWidth: 75
                                horizontalAlignment: Text.AlignRight
                            }
                            Text {
                                text: Strings.thWeight
                                color: Theme.textMuted
                                font.pixelSize: 11
                                font.weight: Font.Bold
                                Layout.preferredWidth: 65
                                Layout.minimumWidth: 65
                                Layout.maximumWidth: 65
                                horizontalAlignment: Text.AlignRight
                            }
                            Text {
                                text: Strings.thActions
                                color: Theme.textMuted
                                font.pixelSize: 11
                                font.weight: Font.Bold
                                Layout.preferredWidth: 195
                                Layout.minimumWidth: 195
                                Layout.maximumWidth: 195
                                horizontalAlignment: Text.AlignRight
                            }
                        }
                    }

                    // Dinamik Pozisyon Satırları (ListView)
                    ListView {
                        id: positionsListView
                        Layout.fillWidth: true
                        implicitHeight: count * 42
                        model: dashboardController.positionsModel
                        interactive: false

                        delegate: Rectangle {
                            id: posRow
                            width: positionsListView.width
                            height: 40
                            radius: Theme.radiusSm

                            // Flash Animation: Fiyat arttığında yeşil, düştüğünde kırmızı yanıp sönme
                            color: {
                                if (model.flashState === 1) return Theme.bullGreenSoft
                                if (model.flashState === 2) return Theme.bearRedSoft
                                return rowMouse.containsMouse ? Theme.bgCardHover : "transparent"
                            }

                            Behavior on color { ColorAnimation { duration: 250 } }

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 12
                                anchors.rightMargin: 12
                                spacing: 8

                                // Sembol & İsim
                                Column {
                                    Layout.fillWidth: true
                                    Layout.minimumWidth: 160
                                    spacing: 2
                                    Text {
                                        text: (model.ticker || "").replace(/\.IS$/i, "")
                                        font.family: Theme.monoFontFamily
                                        font.pixelSize: Theme.fontBase
                                        font.weight: Font.Bold
                                        color: Theme.textPrimary
                                    }
                                    Text {
                                        text: (model.companyName || "").replace(/\.IS$/i, "")
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontXs
                                        color: Theme.textMuted
                                        elide: Text.ElideRight
                                        width: 150
                                    }
                                }

                                // Lot
                                Text {
                                    text: model.quantity
                                    font.family: Theme.monoFontFamily
                                    font.pixelSize: Theme.fontSm
                                    color: Theme.textSecondary
                                    Layout.preferredWidth: 70
                                    Layout.minimumWidth: 70
                                    Layout.maximumWidth: 70
                                    horizontalAlignment: Text.AlignRight
                                }

                                // Maliyet
                                Text {
                                    text: model.avgCost
                                    font.family: Theme.monoFontFamily
                                    font.pixelSize: Theme.fontSm
                                    color: Theme.textSecondary
                                    Layout.preferredWidth: 85
                                    Layout.minimumWidth: 85
                                    Layout.maximumWidth: 85
                                    horizontalAlignment: Text.AlignRight
                                }

                                // Son Fiyat (Flash durumunda renklendirme)
                                Text {
                                    text: model.currentPrice
                                    font.family: Theme.monoFontFamily
                                    font.pixelSize: Theme.fontSm
                                    font.weight: Font.Bold
                                    color: model.flashState === 1 ? Theme.bullGreen : (model.flashState === 2 ? Theme.bearRed : Theme.textPrimary)
                                    Layout.preferredWidth: 85
                                    Layout.minimumWidth: 85
                                    Layout.maximumWidth: 85
                                    horizontalAlignment: Text.AlignRight
                                }

                                // Günlük Fark %
                                Text {
                                    text: model.dailyDiff
                                    font.family: Theme.monoFontFamily
                                    font.pixelSize: Theme.fontSm
                                    font.weight: Font.DemiBold
                                    color: model.dailyDiff.indexOf("+") !== -1 ? Theme.bullGreen : Theme.bearRed
                                    Layout.preferredWidth: 75
                                    Layout.minimumWidth: 75
                                    Layout.maximumWidth: 75
                                    horizontalAlignment: Text.AlignRight
                                }

                                // Piyasa Değeri
                                Text {
                                    text: model.marketValue
                                    font.family: Theme.monoFontFamily
                                    font.pixelSize: Theme.fontSm
                                    font.weight: Font.DemiBold
                                    color: Theme.textPrimary
                                    Layout.preferredWidth: 115
                                    Layout.minimumWidth: 115
                                    Layout.maximumWidth: 115
                                    horizontalAlignment: Text.AlignRight
                                }

                                // K/Z ₺
                                Text {
                                    text: model.unrealizedPL
                                    font.family: Theme.monoFontFamily
                                    font.pixelSize: Theme.fontSm
                                    font.weight: Font.Bold
                                    color: model.isUp ? Theme.bullGreen : Theme.bearRed
                                    Layout.preferredWidth: 110
                                    Layout.minimumWidth: 110
                                    Layout.maximumWidth: 110
                                    horizontalAlignment: Text.AlignRight
                                }

                                // K/Z %
                                Text {
                                    text: model.unrealizedPLPct
                                    font.family: Theme.monoFontFamily
                                    font.pixelSize: Theme.fontSm
                                    font.weight: Font.Bold
                                    color: model.isUp ? Theme.bullGreen : Theme.bearRed
                                    Layout.preferredWidth: 75
                                    Layout.minimumWidth: 75
                                    Layout.maximumWidth: 75
                                    horizontalAlignment: Text.AlignRight
                                }

                                // Ağırlık
                                Text {
                                    text: model.weight
                                    font.family: Theme.monoFontFamily
                                    font.pixelSize: Theme.fontSm
                                    color: Theme.textSecondary
                                    Layout.preferredWidth: 65
                                    Layout.minimumWidth: 65
                                    Layout.maximumWidth: 65
                                    horizontalAlignment: Text.AlignRight
                                }

                                // Aksiyon Butonları (Al/Sat & Grafik)
                                RowLayout {
                                    Layout.preferredWidth: 195
                                    Layout.minimumWidth: 195
                                    Layout.maximumWidth: 195
                                    spacing: 4
                                    Layout.alignment: Qt.AlignRight

                                    ModernButton {
                                        text: Strings.btnChart
                                        variant: "ghost"
                                        implicitHeight: 26
                                        implicitWidth: 60
                                        onClicked: chartView.loadStock(model.ticker)
                                    }

                                    ModernButton {
                                        text: Strings.dashboardDetailButton
                                        variant: "ghost"
                                        implicitHeight: 26
                                        implicitWidth: 55
                                        onClicked: {
                                            if (typeof stockDetailController !== "undefined") {
                                                stockDetailController.openStock(model.ticker)
                                            }
                                        }
                                    }

                                    ModernButton {
                                        text: Strings.btnTrade
                                        variant: "secondary"
                                        implicitHeight: 26
                                        implicitWidth: 55
                                        onClicked: {
                                            const p = parseFloat(model.currentPrice.replace("₺", "").replace(".", "").replace(",", ".")) || 0.0
                                            tradeModal.open(model.ticker, p)
                                        }
                                    }
                                }
                            }

                            MouseArea {
                                id: rowMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    chartView.loadStock(model.ticker)
                                    if (typeof stockDetailController !== "undefined") {
                                        stockDetailController.openStock(model.ticker)
                                    }
                                }
                            }
                        }
                    }
                        }
                    }
                }
            }
        }
    }

    // --- Modallar & Toast Bildirimi ---
    QuickTradeModal {
        id: tradeModal
    }

    CapitalModal {
        id: capitalModal
    }

    ChartFullscreenModal {
        id: chartModal
    }

    ExcelExportDialog {
        id: excelDialog
        title: Strings.excelDialogTitlePortfolio
        onExportRequested: function(startText, endText, filePath, append) {
            dashboardController.exportToExcelFile(startText, endText, filePath, append)
        }
    }

    ToastNotification {
        id: toast
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        anchors.margins: Theme.spaceLg
    }

    // Python Controller Sinyal Bağlantıları
    Connections {
        target: dashboardController

        function onTradeExecuted(success, message) {
            toast.show(message, success)
        }

        function onCapitalUpdated(success, message) {
            toast.show(message, success)
        }

        function onExcelExported(success, message) {
            toast.show(message, success)
        }

        function onClosingPricesUpdated(success, message) {
            toast.show(message, success)
        }
    }
}
