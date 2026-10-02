import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Hızlı Al/Sat emri: hisse kodu, lot, fiyat, işlem tarihi ve saati. Küçük pencerede kaydırılabilir.
Rectangle {
    id: root

    property bool isOpen: false
    property string defaultTicker: "THYAO"
    property real defaultPrice: 0
    property string side: "BUY"
    property string companyName: ""
    property string lookupHint: ""

    readonly property bool isBuy: side === "BUY"
    readonly property real totalValue: (parseFloat(qtyInput.text.replace(",", ".")) || 0) * (parseFloat(priceInput.text.replace(",", ".")) || 0)

    signal closed()

    anchors.fill: parent
    color: "#80000000"
    visible: opacity > 0
    opacity: isOpen ? 1.0 : 0.0
    z: 1000

    Behavior on opacity { NumberAnimation { duration: 180 } }

    function todayText() {
        const d = new Date()
        return String(d.getDate()).padStart(2, "0") + "." + String(d.getMonth() + 1).padStart(2, "0") + "." + d.getFullYear()
    }

    function nowText() {
        const d = new Date()
        return String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0")
    }

    // Hisse kodundan şirket adı ve son bilinen fiyatı doldurur (yalnızca yerel veritabanı)
    function lookup(fillPrice) {
        companyName = ""
        lookupHint = ""
        if (typeof dashboardController === "undefined") return
        const info = dashboardController.lookupTicker(tickerInput.text)
        if (info.found) {
            companyName = info.name
            if (fillPrice && info.price > 0) priceInput.text = info.price.toFixed(2)
        } else if (tickerInput.text.trim() !== "") {
            lookupHint = Strings.tradeTickerUnknown
        }
    }

    function open(ticker, price) {
        if (ticker) root.defaultTicker = ticker
        root.defaultPrice = price || 0
        tickerInput.text = root.defaultTicker
        priceInput.text = root.defaultPrice > 0 ? root.defaultPrice.toFixed(2) : ""
        qtyInput.text = "100"
        dateInput.text = todayText()
        timeInput.text = nowText()
        side = "BUY"
        lookup(root.defaultPrice <= 0)
        root.isOpen = true
    }

    function close() {
        root.isOpen = false
        root.closed()
    }

    MouseArea {
        anchors.fill: parent
        onClicked: root.close()
    }

    ModernCard {
        id: dialogCard
        anchors.centerIn: parent
        width: Math.min(440, root.width - 24)
        implicitHeight: formColumn.implicitHeight + Theme.spaceLg * 2
        height: Math.min(root.height - 24, implicitHeight)
        scale: root.isOpen ? 1.0 : 0.95

        Behavior on scale { NumberAnimation { duration: 200; easing.type: Easing.OutBack } }

        MouseArea { anchors.fill: parent }

        Flickable {
            anchors.fill: parent
            anchors.margins: Theme.spaceLg
            contentWidth: width
            contentHeight: formColumn.implicitHeight
            clip: true
            ScrollBar.vertical: ModernScrollBar {}

            ColumnLayout {
                id: formColumn
                width: parent.width
                spacing: Theme.spaceMd

                // Başlık & Kapat Butonu
                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: Strings.modalTradeTitle
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontLg
                        font.weight: Font.Bold
                        color: Theme.textPrimary
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                    }
                    Item {
                        width: 24
                        height: 24
                        ModernIcon { name: "close"; size: 16; color: Theme.textMuted; anchors.centerIn: parent }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.close()
                        }
                    }
                }

                // İşlem Yönü (ALIŞ / SATIŞ)
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceSm

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        implicitHeight: 36
                        radius: Theme.radiusSm
                        color: root.isBuy ? Theme.bullGreen : Theme.bgInput
                        border.color: root.isBuy ? Theme.bullGreen : Theme.borderSubtle

                        Text {
                            anchors.centerIn: parent
                            text: Strings.btnBuyOrder
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.Bold
                            color: root.isBuy ? "#ffffff" : Theme.textSecondary
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.side = "BUY"
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        implicitHeight: 36
                        radius: Theme.radiusSm
                        color: !root.isBuy ? Theme.bearRed : Theme.bgInput
                        border.color: !root.isBuy ? Theme.bearRed : Theme.borderSubtle

                        Text {
                            anchors.centerIn: parent
                            text: Strings.btnSellOrder
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.Bold
                            color: !root.isBuy ? "#ffffff" : Theme.textSecondary
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.side = "SELL"
                        }
                    }
                }

                // Hisse Sembolü
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Text { text: Strings.labelStockTicker; font.pixelSize: 11; font.weight: Font.Bold; color: Theme.textMuted }
                    ModernInput {
                        id: tickerInput
                        Layout.fillWidth: true
                        implicitHeight: 38
                        font.family: Theme.monoFontFamily
                        font.weight: Font.Bold
                        onEditingFinished: root.lookup(true)
                    }
                    Text {
                        visible: root.companyName !== "" || root.lookupHint !== ""
                        text: root.companyName !== "" ? root.companyName : root.lookupHint
                        color: root.companyName !== "" ? Theme.textSecondary : Theme.warning
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                }

                // Lot ve Fiyat
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceMd

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        spacing: 4
                        Text { text: Strings.labelLot; font.pixelSize: 11; font.weight: Font.Bold; color: Theme.textMuted }
                        ModernInput {
                            id: qtyInput
                            Layout.fillWidth: true
                            implicitHeight: 38
                            font.family: Theme.monoFontFamily
                            validator: IntValidator { bottom: 1; top: 1000000 }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        spacing: 4
                        Text { text: Strings.labelUnitPriceTRY; font.pixelSize: 11; font.weight: Font.Bold; color: Theme.textMuted }
                        ModernInput {
                            id: priceInput
                            Layout.fillWidth: true
                            implicitHeight: 38
                            font.family: Theme.monoFontFamily
                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                        }
                    }
                }

                // Tarih ve Saat
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceMd

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        spacing: 4
                        Text { text: Strings.portfolioTradeLabelDate + " (GG.AA.YYYY)"; font.pixelSize: 11; font.weight: Font.Bold; color: Theme.textMuted; elide: Text.ElideRight; Layout.fillWidth: true }
                        ModernInput {
                            id: dateInput
                            Layout.fillWidth: true
                            implicitHeight: 38
                            font.family: Theme.monoFontFamily
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        spacing: 4
                        Text { text: Strings.portfolioTradeLabelTime + " (SS:DD)"; font.pixelSize: 11; font.weight: Font.Bold; color: Theme.textMuted; elide: Text.ElideRight; Layout.fillWidth: true }
                        ModernInput {
                            id: timeInput
                            Layout.fillWidth: true
                            implicitHeight: 38
                            font.family: Theme.monoFontFamily
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

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        Text {
                            text: Strings.labelEstimatedTotal
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            color: Theme.textSecondary
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                        Text {
                            text: "₺" + root.totalValue.toLocaleString(Qt.locale("tr_TR"), "f", 2)
                            font.family: Theme.monoFontFamily
                            font.pixelSize: Theme.fontMd
                            font.weight: Font.Bold
                            color: root.isBuy ? Theme.bullGreen : Theme.bearRed
                        }
                    }
                }

                // Mevcut Nakit Bilgisi
                Text {
                    text: Strings.labelCurrentCashPrefix + dashboardController.cashBalance
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    color: Theme.textMuted
                    Layout.alignment: Qt.AlignRight
                }

                // Butonlar
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceSm

                    ModernButton {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        text: Strings.btnCancel
                        variant: "secondary"
                        onClicked: root.close()
                    }

                    ModernButton {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        text: root.isBuy ? Strings.btnBuyConfirm : Strings.btnSellConfirm
                        variant: root.isBuy ? "primary" : "danger"
                        onClicked: {
                            const qty = parseInt(qtyInput.text) || 0
                            const price = parseFloat(priceInput.text.replace(",", ".")) || 0.0
                            const ticker = tickerInput.text.trim().toUpperCase()
                            dashboardController.submitTradeAt(
                                ticker, root.side, qty, price, Strings.quickTradeNote,
                                dateInput.text.trim(), timeInput.text.trim())
                            root.close()
                        }
                    }
                }
            }
        }
    }
}
