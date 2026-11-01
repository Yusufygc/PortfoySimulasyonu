import QtQuick
import QtQuick.Layouts
import "../theme"
import "../components"

Item {
    id: root

    // Geniş pencerede grafik solda, haber paneli sağda; dar pencerede haber paneli grafiğin altına iner
    readonly property bool wide: width >= 1150

    // Sayfa bu yüksekliğin altına inerse kaydırılır (Main.qml activePageMetric)
    readonly property int minContentHeight: wide ? 560 : 960

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spaceMd

        // Üst Başlık
        Column {
            Layout.fillWidth: true
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
            PriceStatusChip {}
        }

        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: root.wide ? 2 : 1
            columnSpacing: Theme.spaceMd
            rowSpacing: Theme.spaceMd

            // TradingView Mum Grafiği & Teknik Analiz
            ModernCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 420

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

            // Şirket ve piyasa haberleri
            NewsPanel {
                Layout.preferredWidth: root.wide ? 380 : -1
                Layout.fillWidth: !root.wide
                Layout.fillHeight: root.wide
                Layout.preferredHeight: root.wide ? -1 : 420
                Layout.minimumHeight: 320
            }
        }
    }

    ChartFullscreenModal {
        id: chartModal
    }
}
