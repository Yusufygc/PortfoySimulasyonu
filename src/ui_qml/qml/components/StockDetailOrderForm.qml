import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Hisse detayı hızlı emir formu: yön, lot, fiyat, işlem zamanı, etki önizlemesi ve onay. Emir durumu bu bileşendedir.
Rectangle {
    id: root
    property bool stacked: false
    property string tradeSide: "BUY"  // "BUY" veya "SELL"
    property int tradeQty: 100
    property string tradeDateText: ""
    property string tradeTimeText: ""
    property real tradePrice: (typeof stockDetailController !== "undefined" && stockDetailController.currentPrice > 0) ? stockDetailController.currentPrice : 10.0
    function resetTradeMoment() {
        const now = new Date()
        const pad = (n) => String(n).padStart(2, "0")
        tradeDateText = now.getFullYear() + "-" + pad(now.getMonth() + 1) + "-" + pad(now.getDate())
        tradeTimeText = pad(now.getHours()) + ":" + pad(now.getMinutes())
    }
    // Denetleyicideki güncel fiyatı forma yansıtır (hisse değişince ve modal açılınca çağrılır)
    function syncPrice() {
        if (typeof stockDetailController !== "undefined" && stockDetailController && stockDetailController.currentPrice > 0) {
            root.tradePrice = stockDetailController.currentPrice
            txtPrice.text = stockDetailController.currentPrice.toFixed(2)
        }
    }
    Component.onCompleted: resetTradeMoment()
    Layout.fillWidth: root.stacked
    Layout.preferredWidth: root.stacked ? -1 : 320
    Layout.preferredHeight: 520
    Layout.fillHeight: true
    radius: Theme.radiusSm
    color: Theme.bgCard
    border.color: Theme.borderSubtle
    border.width: 1

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 12

        Text {
            text: Strings.stockDetailQuickTrade
            color: Theme.textPrimary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSm
            font.weight: Font.Bold
        }

        // Alış / Satış Seçim Butonları
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Rectangle {
                Layout.fillWidth: true
                height: 34
                radius: Theme.radiusSm
                color: root.tradeSide === "BUY" ? Theme.bullGreen : Theme.bgSecondary
                border.color: Theme.bullGreen
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: Strings.stockDetailBuyButton
                    color: root.tradeSide === "BUY" ? "#FFFFFF" : Theme.bullGreen
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.Bold
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.tradeSide = "BUY"
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 34
                radius: Theme.radiusSm
                color: root.tradeSide === "SELL" ? Theme.bearRed : Theme.bgSecondary
                border.color: Theme.bearRed
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: Strings.stockDetailSellButton
                    color: root.tradeSide === "SELL" ? "#FFFFFF" : Theme.bearRed
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.Bold
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.tradeSide = "SELL"
                }
            }
        }

        // Lot Adedi Girişi
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4

            Text {
                text: Strings.stockDetailLotLabel
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
            }

            Rectangle {
                Layout.fillWidth: true
                height: 34
                radius: Theme.radiusSm
                color: Theme.bgInput
                border.color: Theme.borderSubtle
                border.width: 1

                TextInput {
                    id: txtQty
                    anchors.fill: parent
                    anchors.margins: 8
                    text: root.tradeQty.toString()
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    font.weight: Font.Bold
                    inputMethodHints: Qt.ImhDigitsOnly
                    onTextChanged: {
                        const q = parseInt(text)
                        if (!isNaN(q) && q > 0) root.tradeQty = q
                    }
                }
            }
        }

        // İşlem Fiyatı Girişi
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4

            Text {
                text: Strings.stockDetailPriceLabel
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
            }

            Rectangle {
                Layout.fillWidth: true
                height: 34
                radius: Theme.radiusSm
                color: Theme.bgInput
                border.color: Theme.borderSubtle
                border.width: 1

                TextInput {
                    id: txtPrice
                    anchors.fill: parent
                    anchors.margins: 8
                    text: root.tradePrice.toFixed(2)
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    font.weight: Font.Bold
                    onTextChanged: {
                        const p = parseFloat(text.replace(",", "."))
                        if (!isNaN(p) && p > 0) root.tradePrice = p
                    }
                }
            }
        }

        // İşlem Tarihi ve Saati
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Repeater {
                model: [
                { label: Strings.stockDetailDateLabel, field: "date" },
                { label: Strings.stockDetailTimeLabel, field: "time" }
                ]

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    Text {
                        text: modelData.label
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 34
                        radius: Theme.radiusSm
                        color: Theme.bgInput
                        border.color: momentInput.activeFocus ? Theme.borderFocus : Theme.borderSubtle
                        border.width: 1

                        TextInput {
                            id: momentInput
                            anchors.fill: parent
                            anchors.margins: 8
                            text: modelData.field === "date" ? root.tradeDateText : root.tradeTimeText
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.Bold
                            onTextEdited: {
                                if (modelData.field === "date") root.tradeDateText = text
                                else root.tradeTimeText = text
                            }
                        }
                    }
                }
            }
        }

        // Toplam Tutar Önizlemesi
        Rectangle {
            Layout.fillWidth: true
            height: 48
            radius: Theme.radiusSm
            color: Theme.bgSecondary
            border.color: Theme.borderSubtle
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.margins: 10

                Text {
                    text: Strings.stockDetailTotalLabel
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                }

                Text {
                    text: "₺" + (root.tradeQty * root.tradePrice).toLocaleString(Qt.locale("tr_TR"), "f", 2)
                    color: root.tradeSide === "BUY" ? Theme.bullGreen : Theme.bearRed
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    font.weight: Font.Bold
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignRight
                }
            }
        }

        // İşlem Etkisi Tahmini
        Rectangle {
            id: impactBox
            Layout.fillWidth: true
            implicitHeight: impactCol.implicitHeight + 16
            radius: Theme.radiusSm
            color: Theme.bgSecondary
            border.color: impact.valid ? Theme.borderSubtle : Theme.bearRed

            property var impact: {
                if (typeof stockDetailController === "undefined") return ({ valid: false, message: "" })
                stockDetailController.quantity
                stockDetailController.avgCost
                return stockDetailController.tradeImpact(root.tradeSide, root.tradeQty, root.tradePrice)
            }

            ColumnLayout {
                id: impactCol
                anchors.fill: parent
                anchors.margins: 8
                spacing: 3

                Text {
                    text: Strings.stockDetailImpactTitle
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.Bold
                }

                Repeater {
                    model: [
                    { label: Strings.stockDetailImpactLot, value: impactBox.impact.newQty || "-" },
                    { label: Strings.stockDetailImpactAvg, value: impactBox.impact.newAvg || "-" },
                    { label: Strings.stockDetailImpactCash, value: impactBox.impact.cashAfter || "-" }
                    ]
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: modelData.label; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; Layout.fillWidth: true; elide: Text.ElideRight }
                        Text { text: modelData.value; color: Theme.textPrimary; font.family: Theme.fontMono; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold }
                    }
                }

                Text {
                    visible: impactBox.impact.message !== undefined && impactBox.impact.message !== ""
                    text: impactBox.impact.message || ""
                    color: Theme.bearRed
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.DemiBold
                }
            }
        }

        Item { Layout.fillHeight: true }

        // Emri Gönder Butonu
        Rectangle {
            Layout.fillWidth: true
            height: 40
            radius: Theme.radiusSm
            color: root.tradeSide === "BUY" ? Theme.bullGreen : Theme.bearRed

            Text {
                anchors.centerIn: parent
                text: (root.tradeSide === "BUY" ? Strings.stockDetailConfirmBuy : Strings.stockDetailConfirmSell)
                color: "#FFFFFF"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                font.weight: Font.Bold
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    if (typeof stockDetailController !== "undefined") {
                        stockDetailController.submitTrade(
                        root.tradeSide,
                        root.tradeQty,
                        root.tradePrice,
                        root.tradeDateText.trim(),
                        root.tradeTimeText.trim()
                        )
                    }
                }
            }
        }
    }
}
