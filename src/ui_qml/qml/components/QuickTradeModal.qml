import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

Rectangle {
    id: root

    property bool isOpen: false
    property string defaultTicker: "THYAO"
    property real defaultPrice: 294.25

    signal closed()

    anchors.fill: parent
    color: "#80000000"
    visible: opacity > 0
    opacity: isOpen ? 1.0 : 0.0

    Behavior on opacity { NumberAnimation { duration: 180 } }

    MouseArea {
        anchors.fill: parent
        onClicked: root.close()
    }

    ModernCard {
        id: dialogCard
        anchors.centerIn: parent
        width: 420
        implicitHeight: 460
        scale: root.isOpen ? 1.0 : 0.95

        Behavior on scale { NumberAnimation { duration: 200; easing.type: Easing.OutBack } }

        MouseArea {
            anchors.fill: parent
            // Diyalog içine tıklayınca kapanmayı engelle
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Theme.spaceLg
            spacing: Theme.spaceMd

            // Başlık & Kapat Butonu
            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: "Hisse Alım / Satım Emri"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontLg
                    font.weight: Font.Bold
                    color: Theme.textPrimary
                    Layout.fillWidth: true
                }
                Text {
                    text: "✕"
                    font.pixelSize: 16
                    color: Theme.textMuted
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.close()
                    }
                }
            }

            // İşlem Yönü Toggle (ALIŞ / SATIŞ)
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 36
                    radius: Theme.radiusSm
                    color: isBuy ? Theme.bullGreen : Theme.bgInput
                    border.color: isBuy ? Theme.bullGreen : Theme.borderSubtle
                    border.width: 1

                    property bool isBuy: sideToggle.state === "BUY"

                    Text {
                        anchors.centerIn: parent
                        text: "▲ HİSSE AL (BUY)"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        font.weight: Font.Bold
                        color: parent.isBuy ? "#ffffff" : Theme.textSecondary
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: sideToggle.state = "BUY"
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 36
                    radius: Theme.radiusSm
                    color: !isBuy ? Theme.bearRed : Theme.bgInput
                    border.color: !isBuy ? Theme.bearRed : Theme.borderSubtle
                    border.width: 1

                    property bool isBuy: sideToggle.state === "BUY"

                    Text {
                        anchors.centerIn: parent
                        text: "▼ HİSSE SAT (SELL)"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        font.weight: Font.Bold
                        color: !parent.isBuy ? "#ffffff" : Theme.textSecondary
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: sideToggle.state = "SELL"
                    }
                }
            }

            Item { id: sideToggle; state: "BUY" }

            // Hisse Sembolü
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                Text { text: "Hisse Kodu (Ticker)"; font.pixelSize: 11; font.weight: Font.Bold; color: Theme.textMuted }
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 38
                    radius: Theme.radiusSm
                    color: Theme.bgInput
                    border.color: tickerInput.activeFocus ? Theme.borderFocus : Theme.borderSubtle
                    border.width: 1

                    TextInput {
                        id: tickerInput
                        anchors.fill: parent
                        anchors.margins: 10
                        text: root.defaultTicker
                        font.family: Theme.monoFontFamily
                        font.pixelSize: Theme.fontBase
                        font.weight: Font.Bold
                        color: Theme.textPrimary
                    }
                }
            }

            // Lot ve Fiyat Yan Yana
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceMd

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Text { text: "Lot Adedi"; font.pixelSize: 11; font.weight: Font.Bold; color: Theme.textMuted }
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 38
                        radius: Theme.radiusSm
                        color: Theme.bgInput
                        border.color: qtyInput.activeFocus ? Theme.borderFocus : Theme.borderSubtle
                        border.width: 1

                        TextInput {
                            id: qtyInput
                            anchors.fill: parent
                            anchors.margins: 10
                            text: "100"
                            font.family: Theme.monoFontFamily
                            font.pixelSize: Theme.fontBase
                            color: Theme.textPrimary
                            validator: IntValidator { bottom: 1; top: 1000000 }
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Text { text: "Birim Fiyat (₺)"; font.pixelSize: 11; font.weight: Font.Bold; color: Theme.textMuted }
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 38
                        radius: Theme.radiusSm
                        color: Theme.bgInput
                        border.color: priceInput.activeFocus ? Theme.borderFocus : Theme.borderSubtle
                        border.width: 1

                        TextInput {
                            id: priceInput
                            anchors.fill: parent
                            anchors.margins: 10
                            text: root.defaultPrice.toFixed(2)
                            font.family: Theme.monoFontFamily
                            font.pixelSize: Theme.fontBase
                            color: Theme.textPrimary
                            validator: DoubleValidator { bottom: 0.01; top: 1000000.0; decimals: 2 }
                        }
                    }
                }
            }

            // Toplam Tutar Özeti
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 50
                radius: Theme.radiusSm
                color: Theme.bgInput
                border.color: Theme.borderSubtle
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    Text {
                        text: "Tahmini Toplam Tutar:"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        color: Theme.textSecondary
                        Layout.fillWidth: true
                    }
                    Text {
                        readonly property real totalVal: (parseFloat(qtyInput.text) || 0) * (parseFloat(priceInput.text) || 0)
                        text: "₺" + totalVal.toLocaleString(Qt.locale("tr_TR"), "f", 2)
                        font.family: Theme.monoFontFamily
                        font.pixelSize: Theme.fontMd
                        font.weight: Font.Bold
                        color: sideToggle.state === "BUY" ? Theme.bullGreen : Theme.bearRed
                    }
                }
            }

            // Mevcut Nakit Bilgisi
            Text {
                text: "Mevcut Nakit Bakiye: " + dashboardController.cashBalance
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                color: Theme.textMuted
                Layout.alignment: Qt.AlignRight
            }

            Item { Layout.fillHeight: true }

            // Butonlar
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm

                ModernButton {
                    Layout.fillWidth: true
                    text: "İptal"
                    variant: "secondary"
                    onClicked: root.close()
                }

                ModernButton {
                    Layout.fillWidth: true
                    text: sideToggle.state === "BUY" ? "Alım Emrini Onayla" : "Satış Emrini Onayla"
                    variant: sideToggle.state === "BUY" ? "primary" : "danger"
                    onClicked: {
                        const qty = parseInt(qtyInput.text) || 0
                        const price = parseFloat(priceInput.text) || 0.0
                        const ticker = tickerInput.text.trim().toUpperCase()
                        dashboardController.submitTrade(ticker, sideToggle.state, qty, price, "Hızlı Emir")
                        root.close()
                    }
                }
            }
        }
    }

    function open(ticker, price) {
        if (ticker) root.defaultTicker = ticker
        if (price) root.defaultPrice = price
        tickerInput.text = root.defaultTicker
        priceInput.text = root.defaultPrice.toFixed(2)
        root.isOpen = true
    }

    function close() {
        root.isOpen = false
        root.closed()
    }
}
