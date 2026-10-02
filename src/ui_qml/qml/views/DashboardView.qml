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

            // Üst Başlık ve Aksiyon Butonları
            RowLayout {
                Layout.fillWidth: true

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
                }

                Item { Layout.fillWidth: true }

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

                // Sermaye Yönetimi Butonu
                ModernButton {
                    text: Strings.btnCapital
                    iconName: "capital"
                    variant: "secondary"
                    onClicked: capitalModal.open()
                }

                // Hızlı Al/Sat Butonu
                ModernButton {
                    text: Strings.btnQuickTrade
                    iconName: "zap"
                    variant: "primary"
                    onClicked: tradeModal.open(chartView.ticker, 294.25)
                }
            }

            // 1. KPI Metrik Kartları (4 Adet)
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceMd

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

            // 2. Orta Blok: TradingView Grafiği & Portföy Dağılımı Donut
            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 520
                spacing: Theme.spaceMd

                // Sol: TradingView Mum Grafiği & Teknik Analiz
                ModernCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

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
                    Layout.preferredWidth: 320
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

                            Text { text: Strings.thSymbolCompany; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 160 }
                            Text { text: Strings.thQuantity; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 70; horizontalAlignment: Text.AlignRight }
                            Text { text: Strings.thAvgCost; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 90; horizontalAlignment: Text.AlignRight }
                            Text { text: Strings.thLastPrice; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 90; horizontalAlignment: Text.AlignRight }
                            Text { text: Strings.thDailyChange; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 80; horizontalAlignment: Text.AlignRight }
                            Text { text: Strings.thMarketValue; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 110; horizontalAlignment: Text.AlignRight }
                            Text { text: Strings.thPLTRY; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 100; horizontalAlignment: Text.AlignRight }
                            Text { text: Strings.thPLPct; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 80; horizontalAlignment: Text.AlignRight }
                            Text { text: Strings.thWeight; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 70; horizontalAlignment: Text.AlignRight }
                            Text { text: Strings.thActions; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }
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

                                // Sembol & İsim
                                Column {
                                    Layout.preferredWidth: 160
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
                                    horizontalAlignment: Text.AlignRight
                                }

                                // Maliyet
                                Text {
                                    text: model.avgCost
                                    font.family: Theme.monoFontFamily
                                    font.pixelSize: Theme.fontSm
                                    color: Theme.textSecondary
                                    Layout.preferredWidth: 90
                                    horizontalAlignment: Text.AlignRight
                                }

                                // Son Fiyat (Flash durumunda renklendirme)
                                Text {
                                    text: model.currentPrice
                                    font.family: Theme.monoFontFamily
                                    font.pixelSize: Theme.fontSm
                                    font.weight: Font.Bold
                                    color: model.flashState === 1 ? Theme.bullGreen : (model.flashState === 2 ? Theme.bearRed : Theme.textPrimary)
                                    Layout.preferredWidth: 90
                                    horizontalAlignment: Text.AlignRight
                                }

                                // Günlük Fark %
                                Text {
                                    text: model.dailyDiff
                                    font.family: Theme.monoFontFamily
                                    font.pixelSize: Theme.fontSm
                                    font.weight: Font.DemiBold
                                    color: model.dailyDiff.indexOf("+") !== -1 ? Theme.bullGreen : Theme.bearRed
                                    Layout.preferredWidth: 80
                                    horizontalAlignment: Text.AlignRight
                                }

                                // Piyasa Değeri
                                Text {
                                    text: model.marketValue
                                    font.family: Theme.monoFontFamily
                                    font.pixelSize: Theme.fontSm
                                    font.weight: Font.DemiBold
                                    color: Theme.textPrimary
                                    Layout.preferredWidth: 110
                                    horizontalAlignment: Text.AlignRight
                                }

                                // K/Z ₺
                                Text {
                                    text: model.unrealizedPL
                                    font.family: Theme.monoFontFamily
                                    font.pixelSize: Theme.fontSm
                                    font.weight: Font.Bold
                                    color: model.isUp ? Theme.bullGreen : Theme.bearRed
                                    Layout.preferredWidth: 100
                                    horizontalAlignment: Text.AlignRight
                                }

                                // K/Z %
                                Text {
                                    text: model.unrealizedPLPct
                                    font.family: Theme.monoFontFamily
                                    font.pixelSize: Theme.fontSm
                                    font.weight: Font.Bold
                                    color: model.isUp ? Theme.bullGreen : Theme.bearRed
                                    Layout.preferredWidth: 80
                                    horizontalAlignment: Text.AlignRight
                                }

                                // Ağırlık
                                Text {
                                    text: model.weight
                                    font.family: Theme.monoFontFamily
                                    font.pixelSize: Theme.fontSm
                                    color: Theme.textSecondary
                                    Layout.preferredWidth: 70
                                    horizontalAlignment: Text.AlignRight
                                }

                                // Aksiyon Butonları (Al/Sat & Grafik)
                                RowLayout {
                                    Layout.fillWidth: true
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
                                onClicked: chartView.loadStock(model.ticker)
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
    }
}
