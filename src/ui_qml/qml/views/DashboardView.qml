import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    id: root

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: Theme.spaceMd

            // Üst Başlık ve Aksiyon Butonları
            RowLayout {
                Layout.fillWidth: true

                Column {
                    spacing: 2
                    Text {
                        text: "Portföy Genel Bakış"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXl
                        font.weight: Font.Bold
                        color: Theme.textPrimary
                    }
                    Text {
                        text: "Gerçek zamanlı piyasa değerlemeleri, canlı emirler ve varlık dağılımı"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        color: Theme.textMuted
                    }
                }

                Item { Layout.fillWidth: true }

                // Canlı Fiyat Yenile Butonu (Yükleniyor animasyonu ile)
                ModernButton {
                    text: dashboardController.isRefreshing ? "Yenileniyor..." : "Fiyatları Yenile"
                    iconSymbol: "🔄"
                    variant: "secondary"
                    enabled: !dashboardController.isRefreshing
                    onClicked: {
                        dashboardController.refreshMetrics()
                        chartView.loadStock(chartView.ticker)
                    }
                }

                // Sermaye Yönetimi Butonu
                ModernButton {
                    text: "Sermaye Yönetimi"
                    iconSymbol: "💼"
                    variant: "secondary"
                    onClicked: capitalModal.open()
                }

                // Hızlı Al/Sat Butonu
                ModernButton {
                    text: "+ Hızlı Alım / Satım"
                    iconSymbol: "⚡"
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
                    title: "Toplam Portföy Değeri"
                    value: dashboardController.totalValue
                    changeText: dashboardController.dailyGainLossPct
                    isPositive: dashboardController.isDailyPositive
                    subText: "Günlük Değişim"
                    iconSymbol: "💰"
                }

                MetricCard {
                    Layout.fillWidth: true
                    title: "Günlük Kâr / Zarar"
                    value: dashboardController.dailyGainLoss
                    changeText: dashboardController.dailyGainLossPct
                    isPositive: dashboardController.isDailyPositive
                    subText: "Bugünkü Getiri"
                    iconSymbol: "📈"
                }

                MetricCard {
                    Layout.fillWidth: true
                    title: "Toplam Gerçekleşmemiş K/Z"
                    value: dashboardController.totalGainLoss
                    changeText: dashboardController.totalGainLossPct
                    isPositive: dashboardController.isTotalPositive
                    subText: "Maliyet: " + dashboardController.totalCost
                    iconSymbol: "🏆"
                }

                MetricCard {
                    Layout.fillWidth: true
                    title: "Nakit Bakiye & Oran"
                    value: dashboardController.cashBalance
                    changeText: dashboardController.cashRatio
                    isPositive: true
                    subText: dashboardController.holdingsCount + " Açık Pozisyon"
                    iconSymbol: "🏦"
                }
            }

            // 2. Orta Blok: TradingView Grafiği & Portföy Dağılımı Donut
            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 460
                spacing: Theme.spaceMd

                // Sol: TradingView Mum Grafiği
                ModernCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: Theme.spaceSm
                        spacing: Theme.spaceSm

                        // Grafik Üst Kontrol Barı (Hızlı Sembol Seçiciler)
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spaceSm

                            Text {
                                text: "TRADINGVIEW CANLI GRAFİK"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                font.weight: Font.Bold
                                color: Theme.textMuted
                            }

                            Item { Layout.fillWidth: true }

                            Repeater {
                                model: dashboardController ? dashboardController.quickTickers : ["THYAO", "GARAN", "ASELS", "KCHOL"]
                                ModernButton {
                                    text: modelData
                                    variant: (chartView.ticker === modelData || (chartController && chartController.currentTicker === modelData)) ? "primary" : "ghost"
                                    implicitHeight: 26
                                    onClicked: {
                                        chartView.loadStock(modelData)
                                    }
                                }
                            }
                        }

                        // TradingView QML Bileşeni
                        TradingViewChart {
                            id: chartView
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            ticker: chartController ? chartController.currentTicker : "OBAMS.IS"
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
                            text: "Açık Pozisyonlar ve Canlı Değerleme"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontMd
                            font.weight: Font.Bold
                            color: Theme.textPrimary
                            Layout.fillWidth: true
                        }
                        Text {
                            text: "Fiyatlar değiştikçe yeşil/kırmızı yanıp söner • Satıra tıklayarak grafiğini açabilirsiniz"
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

                            Text { text: "SEMBOL & ŞİRKET"; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 160 }
                            Text { text: "LOT"; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 70; horizontalAlignment: Text.AlignRight }
                            Text { text: "MALİYET"; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 90; horizontalAlignment: Text.AlignRight }
                            Text { text: "SON FİYAT"; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 90; horizontalAlignment: Text.AlignRight }
                            Text { text: "GÜNLÜK %"; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 80; horizontalAlignment: Text.AlignRight }
                            Text { text: "PİYASA DEĞERİ"; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 110; horizontalAlignment: Text.AlignRight }
                            Text { text: "K/Z (₺)"; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 100; horizontalAlignment: Text.AlignRight }
                            Text { text: "K/Z %"; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 80; horizontalAlignment: Text.AlignRight }
                            Text { text: "AĞIRLIK"; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 70; horizontalAlignment: Text.AlignRight }
                            Text { text: "İŞLEMLER"; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }
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
                                        text: model.ticker
                                        font.family: Theme.monoFontFamily
                                        font.pixelSize: Theme.fontBase
                                        font.weight: Font.Bold
                                        color: Theme.textPrimary
                                    }
                                    Text {
                                        text: model.companyName
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
                                        text: "Grafik"
                                        variant: "ghost"
                                        implicitHeight: 26
                                        implicitWidth: 60
                                        onClicked: chartView.loadStock(model.ticker)
                                    }

                                    ModernButton {
                                        text: "İşlem"
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
