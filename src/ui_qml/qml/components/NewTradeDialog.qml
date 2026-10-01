import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

Popup {
    id: root

    property string side: "BUY" // "BUY" | "SELL"

    modal: true
    dim: true
    anchors.centerIn: Overlay.overlay
    width: Math.min(460, parent ? parent.width * 0.9 : 460)
    padding: 0
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    background: Rectangle {
        color: Theme.bgCard
        radius: Theme.radiusMd
        border.color: Theme.borderCard
        border.width: 1
    }

    function calculateTotal() {
        var p = parseFloat(txtPrice.text.replace(",", ".")) || 0.0
        var q = parseInt(txtQty.text) || 0
        var tot = p * q
        return tot.toLocaleString(Qt.locale("tr_TR"), 'f', 2) + " ₺"
    }

    onOpened: {
        txtTicker.text = ""
        txtQty.text = "100"
        txtPrice.text = ""
        side = "BUY"
        var today = new Date()
        var yyyy = today.getFullYear()
        var mm = String(today.getMonth() + 1).padStart(2, '0')
        var dd = String(today.getDate()).padStart(2, '0')
        txtDate.text = yyyy + "-" + mm + "-" + dd
        var hh = String(today.getHours()).padStart(2, '0')
        var min = String(today.getMinutes()).padStart(2, '0')
        txtTime.text = hh + ":" + min
        txtTicker.forceActiveFocus()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spaceLg
        spacing: Theme.spaceMd

        // Başlık & Kapat Butonu
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            ModernIcon {
                iconSource: Icons.get("trade")
                iconColor: root.side === "BUY" ? Theme.bullGreen : Theme.bearRed
                width: 20
                height: 20
            }

            Text {
                text: Strings.portfolioTradeTitle
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontLg
                font.weight: Font.DemiBold
                Layout.fillWidth: true
            }

            Rectangle {
                width: 28
                height: 28
                radius: Theme.radiusSm
                color: closeMouseArea.containsMouse ? Theme.bgCardHover : "transparent"

                ModernIcon {
                    anchors.centerIn: parent
                    iconSource: Icons.get("close")
                    iconColor: Theme.textMuted
                    width: 14
                    height: 14
                }

                MouseArea {
                    id: closeMouseArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.close()
                }
            }
        }

        // Nakit Bilgi Çubuğu
        Rectangle {
            Layout.fillWidth: true
            height: 32
            radius: Theme.radiusSm
            color: Theme.bgSecondary
            border.color: Theme.borderSubtle
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.spaceSm
                anchors.rightMargin: Theme.spaceSm

                ModernIcon {
                    iconSource: Icons.get("wallet")
                    iconColor: Theme.accent
                    width: 14
                    height: 14
                }

                Text {
                    text: Strings.portfolioKpiCash + ":"
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                }

                Text {
                    text: portfolioController.summaryRemainingCash
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    font.weight: Font.DemiBold
                    Layout.fillWidth: true
                }
            }
        }

        // Alım / Satım Seçici (Toggle)
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            Rectangle {
                Layout.fillWidth: true
                height: 38
                radius: Theme.radiusSm
                color: root.side === "BUY" ? Theme.bullGreen : Theme.bgSecondary
                border.color: root.side === "BUY" ? Theme.bullGreen : Theme.borderSubtle
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: Theme.spaceXs

                    ModernIcon {
                        iconSource: Icons.get("trendingUp")
                        iconColor: root.side === "BUY" ? Theme.textInverse : Theme.bullGreen
                        width: 16
                        height: 16
                    }

                    Text {
                        text: Strings.btnBuy
                        color: root.side === "BUY" ? Theme.textInverse : Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        font.weight: Font.DemiBold
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.side = "BUY"
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 38
                radius: Theme.radiusSm
                color: root.side === "SELL" ? Theme.bearRed : Theme.bgSecondary
                border.color: root.side === "SELL" ? Theme.bearRed : Theme.borderSubtle
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: Theme.spaceXs

                    ModernIcon {
                        iconSource: Icons.get("trendingDown")
                        iconColor: root.side === "SELL" ? Theme.textInverse : Theme.bearRed
                        width: 16
                        height: 16
                    }

                    Text {
                        text: Strings.btnSell
                        color: root.side === "SELL" ? Theme.textInverse : Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        font.weight: Font.DemiBold
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.side = "SELL"
                }
            }
        }

        // Ticker & Lot
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceMd

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceXs

                Text {
                    text: Strings.portfolioTradeLabelTicker
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                }

                TextField {
                    id: txtTicker
                    Layout.fillWidth: true
                    placeholderText: Strings.portfolioTradePlaceholder
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    font.capitalization: Font.AllUppercase
                    leftPadding: Theme.spaceSm
                    rightPadding: Theme.spaceSm

                    background: Rectangle {
                        color: Theme.bgInput
                        radius: Theme.radiusSm
                        border.color: txtTicker.activeFocus ? Theme.borderFocus : Theme.borderSubtle
                        border.width: 1
                    }

                    onEditingFinished: {
                        var ticker = txtTicker.text.trim().toUpperCase()
                        if (ticker !== "") {
                            var p = portfolioController.getLatestPriceForTicker(ticker)
                            if (p > 0) {
                                txtPrice.text = p.toFixed(2)
                            }
                        }
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceXs

                Text {
                    text: Strings.portfolioTradeLabelQty
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 40
                    color: Theme.bgInput
                    radius: Theme.radiusSm
                    border.color: txtQty.activeFocus ? Theme.borderFocus : Theme.borderSubtle
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.spaceSm
                        anchors.rightMargin: Theme.spaceSm
                        spacing: Theme.spaceXs

                        TextField {
                            id: txtQty
                            Layout.fillWidth: true
                            text: "100"
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBase
                            inputMethodHints: Qt.ImhDigitsOnly
                            background: null
                            leftPadding: 0
                            rightPadding: 0
                        }

                        Text {
                            text: "Lot"
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                        }
                    }
                }
            }
        }

        // Fiyat
        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceXs

            Text {
                text: Strings.portfolioTradeLabelPrice
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
            }

            TextField {
                id: txtPrice
                Layout.fillWidth: true
                placeholderText: "0.00"
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBase
                leftPadding: Theme.spaceSm
                rightPadding: Theme.spaceSm
                inputMethodHints: Qt.ImhFormattedNumbersOnly

                background: Rectangle {
                    color: Theme.bgInput
                    radius: Theme.radiusSm
                    border.color: txtPrice.activeFocus ? Theme.borderFocus : Theme.borderSubtle
                    border.width: 1
                }
            }
        }

        // Tarih & Saat
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceMd

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceXs

                Text {
                    text: Strings.portfolioTradeLabelDate
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                }

                TextField {
                    id: txtDate
                    Layout.fillWidth: true
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    leftPadding: Theme.spaceSm
                    rightPadding: Theme.spaceSm

                    background: Rectangle {
                        color: Theme.bgInput
                        radius: Theme.radiusSm
                        border.color: txtDate.activeFocus ? Theme.borderFocus : Theme.borderSubtle
                        border.width: 1
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceXs

                Text {
                    text: Strings.portfolioTradeLabelTime
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                }

                TextField {
                    id: txtTime
                    Layout.fillWidth: true
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    leftPadding: Theme.spaceSm
                    rightPadding: Theme.spaceSm

                    background: Rectangle {
                        color: Theme.bgInput
                        radius: Theme.radiusSm
                        border.color: txtTime.activeFocus ? Theme.borderFocus : Theme.borderSubtle
                        border.width: 1
                    }
                }
            }
        }

        // Tahmini Toplam Tutar Kutusu
        Rectangle {
            Layout.fillWidth: true
            height: 42
            radius: Theme.radiusSm
            color: Theme.bgSecondary
            border.color: Theme.borderSubtle
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.spaceMd
                anchors.rightMargin: Theme.spaceMd

                Text {
                    text: Strings.labelTotalAmount
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                }

                Item { Layout.fillWidth: true }

                Text {
                    text: root.calculateTotal()
                    color: root.side === "BUY" ? Theme.bullGreen : Theme.bearRed
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontMd
                    font.weight: Font.Bold
                }
            }
        }

        Item { Layout.fillHeight: true }

        // Alt Butonlar
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            Item { Layout.fillWidth: true }

            Rectangle {
                width: 90
                height: 36
                radius: Theme.radiusSm
                color: btnCancelMouse.containsMouse ? Theme.bgCardHover : "transparent"
                border.color: Theme.borderSubtle
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: Strings.btnCancel
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                }

                MouseArea {
                    id: btnCancelMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.close()
                }
            }

            Rectangle {
                width: 130
                height: 36
                radius: Theme.radiusSm
                color: {
                    if (root.side === "BUY") {
                        return btnConfirmMouse.containsMouse ? Theme.bullGreen : Theme.bullGreenSoft
                    } else {
                        return btnConfirmMouse.containsMouse ? Theme.bearRed : Theme.bearRedSoft
                    }
                }

                Text {
                    anchors.centerIn: parent
                    text: Strings.btnExecute
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    font.weight: Font.DemiBold
                }

                MouseArea {
                    id: btnConfirmMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        var ticker = txtTicker.text.trim()
                        var price = parseFloat(txtPrice.text.replace(",", "."))
                        if (!ticker || isNaN(price) || price <= 0) return

                        var qty = parseInt(txtQty.text) || 0
                        if (qty <= 0) return

                        portfolioController.addTrade(
                            ticker,
                            root.side,
                            qty,
                            price,
                            txtDate.text.trim(),
                            txtTime.text.trim()
                        )
                        root.close()
                    }
                }
            }
        }
    }
}
