import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

Rectangle {
    id: root

    property var chartView: null
    signal toggleFullscreen()

    implicitHeight: 42
    color: Theme.bgCard
    radius: Theme.radiusSm
    border.color: Theme.borderSubtle
    border.width: 1

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 8
        anchors.rightMargin: 8
        spacing: 6

        // 1. Sol: Ticker, Şirket Adı ve Canlı Fiyat
        RowLayout {
            spacing: 6
            Layout.alignment: Qt.AlignVCenter

            Text {
                text: chartController ? (chartController.currentTicker || "").replace(/\.IS$/i, "") : "BIST"
                font.family: Theme.monoFontFamily
                font.pixelSize: Theme.fontMd
                font.weight: Font.Bold
                color: Theme.textPrimary
            }

            Text {
                text: chartController && chartController.companyName ? chartController.companyName.replace(/\.IS$/i, "") : ""
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                color: Theme.textMuted
                elide: Text.ElideRight
                Layout.maximumWidth: 120
                visible: root.width > 560 && text.length > 0
            }

            // Canlı Fiyat & Değişim Rozeti
            Rectangle {
                implicitHeight: 22
                implicitWidth: priceRow.implicitWidth + 10
                radius: Theme.radiusSm
                color: (chartController && chartController.isPositive) ? Theme.bullGreenSoft : Theme.bearRedSoft
                visible: chartController && chartController.lastPrice !== "₺0.00"

                Row {
                    id: priceRow
                    anchors.centerIn: parent
                    spacing: 4

                    Text {
                        text: chartController ? chartController.lastPrice : ""
                        font.family: Theme.monoFontFamily
                        font.pixelSize: 11
                        font.weight: Font.Bold
                        color: (chartController && chartController.isPositive) ? Theme.bullGreen : Theme.bearRed
                    }

                    Text {
                        text: chartController ? chartController.priceChange : ""
                        font.family: Theme.monoFontFamily
                        font.pixelSize: 11
                        font.weight: Font.DemiBold
                        color: (chartController && chartController.isPositive) ? Theme.bullGreen : Theme.bearRed
                    }
                }
            }
        }

        Item { Layout.fillWidth: true } // Esnek Ara Boşluk

        // 2. Orta: Zaman Dilimleri (1G, 1H, 1A)
        RowLayout {
            spacing: 2
            Layout.alignment: Qt.AlignVCenter

            Repeater {
                model: [
                    { tf: "1D", label: Strings.tf1D },
                    { tf: "1W", label: Strings.tf1W },
                    { tf: "1M", label: Strings.tf1M }
                ]

                Rectangle {
                    implicitWidth: 28
                    implicitHeight: 24
                    radius: Theme.radiusSm
                    color: (chartController && chartController.currentTimeframe === modelData.tf)
                           ? Theme.accent
                           : (tfMouse.containsMouse ? Theme.bgCardHover : "transparent")

                    Text {
                        anchors.centerIn: parent
                        text: modelData.label
                        font.family: Theme.fontFamily
                        font.pixelSize: 11
                        font.weight: Font.Bold
                        color: (chartController && chartController.currentTimeframe === modelData.tf)
                               ? "#ffffff"
                               : Theme.textSecondary
                    }

                    MouseArea {
                        id: tfMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (chartController) chartController.setTimeframe(modelData.tf)
                        }
                    }
                }
            }
        }

        // Dikey İnce Ayırıcı
        Rectangle {
            implicitWidth: 1
            implicitHeight: 16
            color: Theme.borderSubtle
        }

        // 3. Grafik Tipi Seçimi (Mum, Çizgi, Alan, Bar)
        RowLayout {
            spacing: 2
            Layout.alignment: Qt.AlignVCenter

            Repeater {
                model: [
                    { type: "candle", icon: "candle",    title: Strings.chartCandle },
                    { type: "line",   icon: "line",      title: Strings.chartLine },
                    { type: "area",   icon: "area",      title: Strings.chartArea },
                    { type: "bar",    icon: "barchart",  title: Strings.chartBar }
                ]

                Rectangle {
                    implicitWidth: 26
                    implicitHeight: 24
                    radius: Theme.radiusSm
                    color: (chartController && chartController.currentChartType === modelData.type)
                           ? Theme.accentSoft
                           : (typeMouse.containsMouse ? Theme.bgCardHover : "transparent")
                    border.color: (chartController && chartController.currentChartType === modelData.type)
                                  ? Theme.accent
                                  : "transparent"
                    border.width: 1

                    ModernIcon {
                        anchors.centerIn: parent
                        name: modelData.icon
                        size: 13
                        color: (chartController && chartController.currentChartType === modelData.type)
                               ? Theme.accent
                               : Theme.textSecondary
                    }

                    MouseArea {
                        id: typeMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (chartController) chartController.setChartType(modelData.type)
                        }
                    }
                }
            }
        }

        // Dikey İnce Ayırıcı
        Rectangle {
            implicitWidth: 1
            implicitHeight: 16
            color: Theme.borderSubtle
        }

        // 4. İndikatörler Açılır Menü Butonu
        ModernButton {
            id: btnIndicators
            text: Strings.btnIndicators
            iconName: "layers"
            variant: "secondary"
            implicitHeight: 26
            onClicked: indPopup.open()
        }

        // 5. Otomatik Sığdır Butonu
        ModernButton {
            iconName: "target"
            variant: "ghost"
            implicitHeight: 26
            implicitWidth: 26
            onClicked: {
                if (chartView) chartView.fitContent()
            }
        }

        // 6. Tam Ekran Genişlet Butonu
        ModernButton {
            iconName: "fullscreen"
            variant: "ghost"
            implicitHeight: 26
            implicitWidth: 26
            onClicked: root.toggleFullscreen()
        }
    }

    // --- İndikatörler Açılır Menüsü (Popup) ---
    Popup {
        id: indPopup
        x: btnIndicators.x - 120
        y: btnIndicators.y + btnIndicators.height + 4
        width: 250
        padding: Theme.spaceSm
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            color: Theme.bgSecondary
            radius: Theme.radiusMd
            border.color: Theme.borderCard
            border.width: 1
        }

        contentItem: ColumnLayout {
            spacing: 4

            Text {
                text: Strings.technicalIndicators
                font.family: Theme.fontFamily
                font.pixelSize: 11
                font.weight: Font.Bold
                color: Theme.textMuted
                Layout.leftMargin: 4
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: Theme.borderSubtle
            }

            // İndikatör Listesi
            Repeater {
                model: [
                    { id: "sma20",       label: Strings.chartIndSma20, color: "#00e5ff" },
                    { id: "sma50",       label: Strings.chartIndSma50, color: "#ff9800" },
                    { id: "sma200",      label: Strings.chartIndSma200, color: "#b388ff" },
                    { id: "ema20",       label: Strings.chartIndEma20, color: "#00e676" },
                    { id: "bb",          label: Strings.chartIndBollinger, color: "#2196f3" },
                    { id: "rsi",         label: Strings.chartIndRsi, color: "#e040fb" },
                    { id: "macd",        label: Strings.chartIndMacd, color: "#2962ff" },
                    { id: "markers",     label: Strings.chartIndCrossMarkers, color: "#ffd600" },
                ]

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 28
                    radius: Theme.radiusSm
                    color: itemMouse.containsMouse ? Theme.bgCardHover : "transparent"

                    readonly property bool isChecked: (chartController && chartController.activeIndicators)
                        ? (chartController.activeIndicators.indexOf(modelData.id) !== -1)
                        : false

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 6
                        anchors.rightMargin: 6
                        spacing: 8

                        // Renkli gösterge noktası
                        Rectangle {
                            width: 8
                            height: 8
                            radius: 4
                            color: modelData.color
                        }

                        Text {
                            text: modelData.label
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            color: Theme.textPrimary
                            Layout.fillWidth: true
                        }

                        ModernIcon {
                            name: "check"
                            size: 14
                            color: Theme.accent
                            visible: isChecked
                        }
                    }

                    MouseArea {
                        id: itemMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (chartController) {
                                chartController.toggleIndicator(modelData.id)
                            }
                        }
                    }
                }
            }
        }
    }
}
