import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Ortak nakit havuzunda Döviz Al/Sat: TL ile USD arasında çevirme. Kur, veritabanındaki en yeni USD/TRY kurundan
// önerilir, düzenlenebilir. Alım TL bakiyesini, satım USD bakiyesini aşamaz (denetim servisinde yapılır).
Rectangle {
    id: root

    // Escape tuşu kutuyu kapatır (Popup tabanlı diyaloglarla aynı davranış)
    Shortcut {
        sequence: "Escape"
        enabled: root.isOpen
        onActivated: root.close()
    }

    property bool isOpen: false
    property bool isBuy: true

    readonly property real usdAmount: Numbers.parseOr(amountInput.text, 0)
    readonly property real rate: Numbers.parseOr(rateInput.text, 0)
    readonly property real fee: Numbers.parseOr(feeInput.text, 0)
    // Alımda ödenecek, satımda alınacak TL (ücret dahil)
    readonly property real tryTotal: isBuy ? usdAmount * rate + fee : usdAmount * rate - fee

    signal closed()

    anchors.fill: parent
    color: "#80000000"
    visible: opacity > 0
    opacity: isOpen ? 1.0 : 0.0
    z: 1000

    Behavior on opacity { NumberAnimation { duration: 180 } }

    function open() {
        isBuy = true
        amountInput.text = ""
        feeInput.text = ""
        rateInput.text = cashPoolController.suggestRate()
        dateInput.text = Dates.today()
        timeInput.text = Dates.nowTime()
        root.isOpen = true
    }

    function close() {
        root.isOpen = false
        root.closed()
    }

    Connections {
        target: cashPoolController
        function onNotify(success, message) {
            if (success && root.isOpen) amountInput.text = ""
        }
    }

    MouseArea {
        anchors.fill: parent
        onClicked: root.close()
    }

    ModernCard {
        anchors.centerIn: parent
        width: Math.min(460, parent.width - Theme.spaceLg * 2)
        implicitHeight: Math.min(parent.height - Theme.spaceLg * 2, contentColumn.implicitHeight + Theme.spaceLg * 2)
        scale: root.isOpen ? 1.0 : 0.95

        Behavior on scale { NumberAnimation { duration: 200; easing.type: Easing.OutBack } }

        MouseArea { anchors.fill: parent }

        ScrollView {
            anchors.fill: parent
            anchors.margins: Theme.spaceLg
            clip: true
            contentWidth: availableWidth
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            ColumnLayout {
                id: contentColumn
                width: parent.width
                spacing: Theme.spaceMd

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: Strings.fxTitle
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontLg
                        font.weight: Font.Bold
                        color: Theme.textPrimary
                        Layout.fillWidth: true
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

                // Mevcut bakiyeler
                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: Strings.fxBalanceTry + cashPoolController.tryBalance
                        font.family: Theme.monoFontFamily
                        font.pixelSize: Theme.fontSm
                        color: Theme.textSecondary
                        Layout.fillWidth: true
                    }
                    Text {
                        text: Strings.fxBalanceUsd + cashPoolController.usdBalance
                        font.family: Theme.monoFontFamily
                        font.pixelSize: Theme.fontSm
                        color: Theme.textSecondary
                    }
                }

                // Yön
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
                            text: Strings.fxBuyUsd
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.Bold
                            color: root.isBuy ? "#ffffff" : Theme.textSecondary
                        }
                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.isBuy = true }
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
                            text: Strings.fxSellUsd
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.Bold
                            color: !root.isBuy ? "#ffffff" : Theme.textSecondary
                        }
                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.isBuy = false }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceMd

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        spacing: 4
                        Text { text: Strings.fxLabelUsd; font.pixelSize: 11; font.weight: Font.Bold; color: Theme.textMuted }
                        ModernInput {
                            id: amountInput
                            Layout.fillWidth: true
                            implicitHeight: 38
                            font.family: Theme.monoFontFamily
                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        spacing: 4
                        Text { text: Strings.fxLabelRate; font.pixelSize: 11; font.weight: Font.Bold; color: Theme.textMuted }
                        ModernInput {
                            id: rateInput
                            Layout.fillWidth: true
                            implicitHeight: 38
                            font.family: Theme.monoFontFamily
                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceMd

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        spacing: 4
                        Text { text: Strings.portfolioTradeLabelDate + " (GG.AA.YYYY)"; font.pixelSize: 11; font.weight: Font.Bold; color: Theme.textMuted; elide: Text.ElideRight; Layout.fillWidth: true }
                        ModernInput { id: dateInput; Layout.fillWidth: true; implicitHeight: 38; font.family: Theme.monoFontFamily }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        spacing: 4
                        Text { text: Strings.portfolioTradeLabelTime + " (SS:DD)"; font.pixelSize: 11; font.weight: Font.Bold; color: Theme.textMuted; elide: Text.ElideRight; Layout.fillWidth: true }
                        ModernInput { id: timeInput; Layout.fillWidth: true; implicitHeight: 38; font.family: Theme.monoFontFamily }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Text { text: Strings.fxLabelFee; font.pixelSize: 11; font.weight: Font.Bold; color: Theme.textMuted }
                    ModernInput {
                        id: feeInput
                        Layout.fillWidth: true
                        implicitHeight: 38
                        font.family: Theme.monoFontFamily
                        inputMethodHints: Qt.ImhFormattedNumbersOnly
                    }
                }

                // TL karşılığı
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 46
                    radius: Theme.radiusSm
                    color: Theme.bgInput
                    border.color: Theme.borderSubtle

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        Text {
                            text: root.isBuy ? Strings.fxTotalPay : Strings.fxTotalReceive
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            color: Theme.textSecondary
                            Layout.fillWidth: true
                        }
                        Text {
                            text: root.tryTotal.toLocaleString(Qt.locale("tr_TR"), "f", 2) + " ₺"
                            font.family: Theme.monoFontFamily
                            font.pixelSize: Theme.fontMd
                            font.weight: Font.Bold
                            color: root.isBuy ? Theme.textNegative : Theme.textPositive
                        }
                    }
                }

                // Son döviz işlemleri (silinebilir)
                Text {
                    visible: cashPoolController.conversions.length > 0
                    text: Strings.fxHistory
                    font.pixelSize: 11
                    font.weight: Font.Bold
                    color: Theme.textMuted
                }

                Repeater {
                    model: cashPoolController.conversions.slice(0, 5)

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: modelData.text
                            font.family: Theme.monoFontFamily
                            font.pixelSize: Theme.fontXs
                            color: Theme.textSecondary
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                        Item {
                            width: 20
                            height: 20
                            ModernIcon { name: "close"; size: 12; color: Theme.textMuted; anchors.centerIn: parent }
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: cashPoolController.deleteConversion(modelData.id)
                            }
                        }
                    }
                }

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
                        text: root.isBuy ? Strings.fxBuyUsd : Strings.fxSellUsd
                        variant: root.isBuy ? "primary" : "danger"
                        onClicked: {
                            const args = [amountInput.text, rateInput.text, dateInput.text.trim(), timeInput.text.trim(), feeInput.text]
                            if (root.isBuy) cashPoolController.buyUsd(args[0], args[1], args[2], args[3], args[4])
                            else cashPoolController.sellUsd(args[0], args[1], args[2], args[3], args[4])
                        }
                    }
                }
            }
        }
    }
}
