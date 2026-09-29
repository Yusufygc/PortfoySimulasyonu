import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"
import "../components"

ScrollView {
    id: root
    contentWidth: availableWidth
    clip: true

    ColumnLayout {
        width: root.availableWidth
        spacing: Theme.spaceMd

        // Sayfa Başlığı ve Hızlı Butonlar
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
                    text: "Gerçek zamanlı piyasa değerlemeleri ve varlık dağılımı"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    color: Theme.textMuted
                }
            }

            Item { Layout.fillWidth: true }

            ModernButton {
                text: "Yenile"
                iconSymbol: "🔄"
                variant: "secondary"
                onClicked: {
                    dashboardController.refreshMetrics()
                    chartView.loadStock(chartView.ticker)
                }
            }

            ModernButton {
                text: "+ Hızlı İşlem"
                iconSymbol: "⚡"
                variant: "primary"
                onClicked: {
                    // Quick trade modal or page
                }
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
                title: "Toplam Kâr / Zarar"
                value: dashboardController.totalGainLoss
                changeText: dashboardController.totalGainLossPct
                isPositive: dashboardController.isTotalPositive
                subText: "Net Gerçekleşmemiş"
                iconSymbol: "🏆"
            }

            MetricCard {
                Layout.fillWidth: true
                title: "Nakit Oranı"
                value: dashboardController.cashRatio
                changeText: "TCMB %45"
                isPositive: true
                subText: "8 Açık Pozisyon"
                iconSymbol: "🏦"
            }
        }

        // 2. Orta Blok: TradingView Grafiği & Portföy Dağılımı
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 460
            spacing: Theme.spaceMd

            // Sol: TradingView Mum Grafiği
            ModernCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredWidth: 65

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spaceSm
                    spacing: Theme.spaceSm

                    // Grafik Üst Kontrol Barı (Sembol Seçiciler)
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm

                        Text {
                            text: "CANLI PİYASA GRAFİĞİ"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            font.weight: Font.Bold
                            color: Theme.textMuted
                        }

                        Item { Layout.fillWidth: true }

                        Repeater {
                            model: ["THYAO", "GARAN", "ASELS", "BIST100"]
                            ModernButton {
                                text: modelData
                                variant: chartView.ticker === modelData ? "primary" : "ghost"
                                implicitHeight: 26
                                onClicked: chartView.loadStock(modelData)
                            }
                        }
                    }

                    // TradingView QML Bileşeni
                    TradingViewChart {
                        id: chartView
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        ticker: "THYAO"
                    }
                }
            }

            // Sağ: Varlık Dağılımı & Hızlı Özet
            ModernCard {
                Layout.preferredWidth: 320
                Layout.fillHeight: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spaceMd
                    spacing: Theme.spaceMd

                    Text {
                        text: "Varlık Dağılımı"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontMd
                        font.weight: Font.Bold
                        color: Theme.textPrimary
                    }

                    // Varlık Dağılım Barları
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm

                        Repeater {
                            model: [
                                { name: "BIST Hisse Senetleri", pct: "68%", color: "#2962ff", value: "₺1.010.221" },
                                { name: "Eurobond / Fonlar",   pct: "19%", color: "#089981", value: "₺282.268" },
                                { name: "TL Nakit & Vadeli",   pct: "13%", color: "#ff9800", value: "₺193.131" },
                            ]

                            Column {
                                Layout.fillWidth: true
                                spacing: 4

                                RowLayout {
                                    width: parent.width
                                    Text {
                                        text: modelData.name
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSm
                                        color: Theme.textSecondary
                                        Layout.fillWidth: true
                                    }
                                    Text {
                                        text: modelData.pct
                                        font.family: Theme.monoFontFamily
                                        font.pixelSize: Theme.fontSm
                                        font.weight: Font.Bold
                                        color: Theme.textPrimary
                                    }
                                }

                                Rectangle {
                                    width: parent.width
                                    height: 6
                                    radius: 3
                                    color: Theme.bgInput

                                    Rectangle {
                                        width: parent.width * (parseInt(modelData.pct) / 100)
                                        height: parent.height
                                        radius: 3
                                        color: modelData.color
                                    }
                                }
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }

                    // Alt Kısayol Bilgilendirmesi
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 70
                        radius: Theme.radiusSm
                        color: Theme.bgInput
                        border.color: Theme.borderSubtle
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 10

                            Text {
                                text: "💡"
                                font.pixelSize: 20
                            }

                            Column {
                                Layout.fillWidth: true
                                spacing: 2
                                Text {
                                    text: "AI Danışman Notu"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                    font.weight: Font.Bold
                                    color: Theme.accent
                                }
                                Text {
                                    text: "Portföy beta katsayısı 1.12. Yüksek volatiliteye karşı nakit oranı dengeli."
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                    color: Theme.textSecondary
                                    wrapMode: Text.WordWrap
                                    width: 220
                                }
                            }
                        }
                    }
                }
            }
        }

        // 3. Alt Blok: Açık Pozisyonlar Tablo Kartı
        ModernCard {
            Layout.fillWidth: true
            implicitHeight: 220

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Theme.spaceMd
                spacing: Theme.spaceSm

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: "Açık Pozisyonlar ve Son Durum"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontMd
                        font.weight: Font.Bold
                        color: Theme.textPrimary
                        Layout.fillWidth: true
                    }
                    Text {
                        text: "Toplam 8 Varlık"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        color: Theme.textMuted
                    }
                }

                // Basit ve Şık Grid Başlıkları
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 32
                    radius: Theme.radiusSm
                    color: Theme.bgInput

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12

                        Text { text: "SEMBOL"; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 80 }
                        Text { text: "LOT"; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 80 }
                        Text { text: "MALİYET"; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 100 }
                        Text { text: "SON FİYAT"; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 100 }
                        Text { text: "GÜNLÜK FARK"; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 100 }
                        Text { text: "TOPLAM DEĞER"; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.fillWidth: true }
                        Text { text: "K/Z %"; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 80 }
                    }
                }

                // Örnek Satırlar
                Repeater {
                    model: [
                        { ticker: "THYAO", lot: "1.250", cost: "₺264,50", price: "₺294,25", diff: "+%2,15", total: "₺367.812,50", pl: "+%11,25", isUp: true },
                        { ticker: "GARAN", lot: "2.800", cost: "₺98,20", price: "₺118,40", diff: "+%1,45", total: "₺331.520,00", pl: "+%20,57", isUp: true },
                        { ticker: "ASELS", lot: "3.500", cost: "₺62,10", price: "₺59,80", diff: "-%0,80", total: "₺209.300,00", pl: "-%3,70", isUp: false },
                    ]

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 36
                        color: rowArea.containsMouse ? Theme.bgCardHover : "transparent"
                        radius: Theme.radiusSm

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12

                            Text { text: modelData.ticker; color: Theme.textPrimary; font.weight: Font.Bold; Layout.preferredWidth: 80 }
                            Text { text: modelData.lot; color: Theme.textSecondary; Layout.preferredWidth: 80 }
                            Text { text: modelData.cost; color: Theme.textSecondary; Layout.preferredWidth: 100 }
                            Text { text: modelData.price; color: Theme.textPrimary; font.weight: Font.DemiBold; Layout.preferredWidth: 100 }
                            Text { text: modelData.diff; color: modelData.isUp ? Theme.bullGreen : Theme.bearRed; font.weight: Font.Bold; Layout.preferredWidth: 100 }
                            Text { text: modelData.total; color: Theme.textPrimary; Layout.fillWidth: true }
                            Text { text: modelData.pl; color: modelData.isUp ? Theme.bullGreen : Theme.bearRed; font.weight: Font.Bold; Layout.preferredWidth: 80 }
                        }

                        MouseArea {
                            id: rowArea
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: chartView.loadStock(modelData.ticker)
                        }
                    }
                }
            }
        }
    }
}
