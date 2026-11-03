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

    // Kayan şerit: portföyden bağımsız rastgele BIST hisseleri (her açılışta yeni seçim)
    readonly property var marketChips: chartController ? chartController.marketTickers : ["OBAMS", "PSGYO", "BINHO"]

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

                    // 2. Kayan BIST hisse şeridi: soldan sağa akar, fare üstündeyken durur
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm

                        Text {
                            text: Strings.tvMarketTickers
                            font.family: Theme.fontFamily
                            font.pixelSize: 11
                            font.weight: Font.Bold
                            color: Theme.textMuted
                            Layout.alignment: Qt.AlignVCenter
                        }

                        Item {
                            id: tickerMarquee
                            Layout.fillWidth: true
                            implicitHeight: 26
                            clip: true

                            // Aynı satır iki kez dizilir; bir satır genişliği kadar kayınca başa sarar (kesintisiz akış)
                            readonly property real loopWidth: firstRow.width + marqueeTrack.spacing
                            readonly property bool scrolls: loopWidth > width

                            HoverHandler { id: marqueeHover }

                            Row {
                                id: marqueeTrack
                                spacing: Theme.spaceXs
                                x: -tickerMarquee.loopWidth

                                NumberAnimation on x {
                                    from: -tickerMarquee.loopWidth
                                    to: 0
                                    duration: Math.max(1000, tickerMarquee.loopWidth * 25)
                                    loops: Animation.Infinite
                                    running: tickerMarquee.scrolls
                                    paused: marqueeHover.hovered
                                }

                                Row {
                                    id: firstRow
                                    spacing: Theme.spaceXs
                                    Repeater {
                                        model: root.marketChips
                                        ModernButton {
                                            text: modelData
                                            variant: (chartController && chartController.currentTicker === modelData) ? "primary" : "ghost"
                                            implicitHeight: 24
                                            onClicked: chartView.loadStock(modelData)
                                        }
                                    }
                                }

                                Row {
                                    spacing: Theme.spaceXs
                                    visible: tickerMarquee.scrolls
                                    Repeater {
                                        model: root.marketChips
                                        ModernButton {
                                            text: modelData
                                            variant: (chartController && chartController.currentTicker === modelData) ? "primary" : "ghost"
                                            implicitHeight: 24
                                            onClicked: chartView.loadStock(modelData)
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
