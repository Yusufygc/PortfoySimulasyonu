import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

Rectangle {
    id: root

    property var chartView: null
    signal toggleFullscreen()

    implicitHeight: 46
    color: Theme.bgCard
    radius: Theme.radiusSm
    border.color: Theme.borderSubtle
    border.width: 1

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.spaceSm
        anchors.rightMargin: Theme.spaceSm
        spacing: Theme.spaceSm

        // 1. Sol: Ticker, Şirket Adı ve Canlı Fiyat
        RowLayout {
            spacing: 8
            Layout.alignment: Qt.AlignVCenter

            Text {
                text: chartController ? chartController.currentTicker : "BIST"
                font.family: Theme.monoFontFamily
                font.pixelSize: Theme.fontMd
                font.weight: Font.Bold
                color: Theme.textPrimary
            }

            Text {
                text: chartController && chartController.companyName ? chartController.companyName : ""
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                color: Theme.textMuted
                elide: Text.ElideRight
                Layout.maximumWidth: 140
                visible: text.length > 0
            }

            // Canlı Fiyat & Değişim Rozeti
            Rectangle {
                implicitHeight: 24
                implicitWidth: priceRow.implicitWidth + 12
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
                        font.pixelSize: Theme.fontXs
                        font.weight: Font.Bold
                        color: (chartController && chartController.isPositive) ? Theme.bullGreen : Theme.bearRed
                    }

                    Text {
                        text: chartController ? chartController.priceChange : ""
                        font.family: Theme.monoFontFamily
                        font.pixelSize: Theme.fontXs
                        font.weight: Font.DemiBold
                        color: (chartController && chartController.isPositive) ? Theme.bullGreen : Theme.bearRed
                    }
                }
            }
        }

        Item { Layout.fillWidth: true }

        // 2. Orta: Zaman Dilimleri (1G, 1H, 1A)
        RowLayout {
            spacing: 2
            Layout.alignment: Qt.AlignVCenter

            Repeater {
                model: [
                    { tf: "1D", label: "1G" },
                    { tf: "1W", label: "1H" },
                    { tf: "1M", label: "1A" }
                ]

                Rectangle {
                    implicitWidth: 32
                    implicitHeight: 26
                    radius: Theme.radiusSm
                    color: (chartController && chartController.currentTimeframe === modelData.tf)
                           ? Theme.accent
                           : (tfMouse.containsMouse ? Theme.bgCardHover : "transparent")

                    Text {
                        anchors.centerIn: parent
                        text: modelData.label
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
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

        // Dikey Ayırıcı
        Rectangle {
            implicitWidth: 1
            implicitHeight: 18
            color: Theme.borderSubtle
        }

        // 3. Grafik Tipi Seçimi (Mum, Çizgi, Alan, Bar)
        RowLayout {
            spacing: 2
            Layout.alignment: Qt.AlignVCenter

            Repeater {
                model: [
                    { type: "candle", icon: "🕯️", title: "Mum" },
                    { type: "line",   icon: "📈", title: "Çizgi" },
                    { type: "area",   icon: "🌊", title: "Alan" },
                    { type: "bar",    icon: "📊", title: "Bar" }
                ]

                Rectangle {
                    implicitWidth: 30
                    implicitHeight: 26
                    radius: Theme.radiusSm
                    color: (chartController && chartController.currentChartType === modelData.type)
                           ? Theme.accentSoft
                           : (typeMouse.containsMouse ? Theme.bgCardHover : "transparent")
                    border.color: (chartController && chartController.currentChartType === modelData.type)
                                  ? Theme.accent
                                  : "transparent"
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: modelData.icon
                        font.pixelSize: 12
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

        // Dikey Ayırıcı
        Rectangle {
            implicitWidth: 1
            implicitHeight: 18
            color: Theme.borderSubtle
        }

        // 4. İndikatörler Açılır Menü Butonu
        ModernButton {
            id: btnIndicators
            text: "İndikatörler ▾"
            iconSymbol: "📐"
            variant: "secondary"
            implicitHeight: 28
            onClicked: indPopup.open()
        }

        // 5. Otomatik Sığdır Butonu
        ModernButton {
            text: ""
            iconSymbol: "🎯"
            variant: "ghost"
            implicitHeight: 28
            implicitWidth: 32
            onClicked: {
                if (chartView) chartView.fitContent()
            }
        }

        // 6. Tam Ekran Genişlet Butonu
        ModernButton {
            text: ""
            iconSymbol: "⛶"
            variant: "ghost"
            implicitHeight: 28
            implicitWidth: 32
            onClicked: root.toggleFullscreen()
        }
    }

    // --- İndikatörler Açılır Menüsü (Popup) ---
    Popup {
        id: indPopup
        x: btnIndicators.x - 120
        y: btnIndicators.y + btnIndicators.height + 6
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
            spacing: 6

            Text {
                text: "TEKNİK İNDİKATÖRLER"
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
                    { id: "sma20",       label: "SMA 20 (Kısa Vade)", color: "#00e5ff" },
                    { id: "sma50",       label: "SMA 50 (Orta Vade)", color: "#ff9800" },
                    { id: "sma200",      label: "SMA 200 (Uzun Vade)", color: "#b388ff" },
                    { id: "ema20",       label: "EMA 20 (Üstel)", color: "#00e676" },
                    { id: "bb",          label: "Bollinger Bantları (20, 2)", color: "#2196f3" },
                    { id: "rsi",         label: "RSI (14) Alt Panel", color: "#e040fb" },
                    { id: "macd",        label: "MACD (12, 26, 9) Alt Panel", color: "#2962ff" },
                    { id: "markers",     label: "Golden / Death Cross Sinyalleri", color: "#ffd600" },
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

                        Text {
                            text: isChecked ? "✓" : ""
                            font.pixelSize: 13
                            font.weight: Font.Bold
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
