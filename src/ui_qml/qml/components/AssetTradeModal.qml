import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// BIST dışı varlık alım/satım kaydı: miktar kesirli olabilir; fiyat varlığın kendi para biriminde, kur işlem anındaki
// "1 birim para birimi = kaç TRY" değeridir (TRY fiyatlı varlıkta gizlenir). Önerilen fiyat ve kur veritabanından gelir.
Rectangle {
    id: root

    property bool isOpen: false
    property string side: "BUY"
    property string currency: "USD"
    property bool isTry: false
    property string availableCash: ""
    property string feeText: ""

    readonly property bool isBuy: side === "BUY"
    readonly property var assetList: assetsController.assets
    readonly property int currentAssetId: (assetList.length > 0 && assetCombo.currentIndex >= 0 && assetCombo.currentIndex < assetList.length)
                                          ? assetList[assetCombo.currentIndex].id : 0
    readonly property real totalValue: (Numbers.parse(qtyInput.text) || 0) * (Numbers.parse(priceInput.text) || 0)

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

    // assetId > 0 ise o varlık seçilir; yoksa ilk varlık
    function open(assetId) {
        let index = 0
        for (let i = 0; i < assetList.length; i++) {
            if (assetList[i].id === assetId) index = i
        }
        assetCombo.currentIndex = index
        side = "BUY"
        qtyInput.text = ""
        dateInput.text = todayText()
        timeInput.text = nowText()
        refreshSuggestion()
        root.isOpen = true
    }

    function close() {
        root.isOpen = false
        root.closed()
    }

    function refreshSuggestion() {
        const id = currentAssetId
        if (id <= 0) return
        const hint = assetsController.suggest(id)
        currency = hint.currency || "USD"
        isTry = hint.isTry === true
        priceInput.text = hint.price || ""
        fxInput.text = hint.fxRate || ""
        availableCash = hint.cash || ""
        refreshFee()
    }

    // Tahmini ücret (ayardaki oranlarla); miktar ya da fiyat eksikse boş
    function refreshFee() {
        feeText = currentAssetId > 0 ? assetsController.estimateFee(currentAssetId, qtyInput.text, priceInput.text) : ""
    }

    Connections {
        target: assetsController
        function onTradeRecorded(success, message) {
            if (success && root.isOpen) root.close()
        }
    }

    MouseArea {
        anchors.fill: parent
        onClicked: root.close()
    }

    ModernCard {
        anchors.centerIn: parent
        width: Math.min(440, parent.width - Theme.spaceLg * 2)
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
                        text: Strings.assetTradeTitle
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

                Text {
                    visible: root.assetList.length === 0
                    text: Strings.assetTradeNoAssets
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    color: Theme.warning
                    Layout.fillWidth: true
                }

                // İşlem yönü
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
                            text: Strings.assetBuy
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
                            text: Strings.assetSell
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

                // Varlık
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Text { text: Strings.assetTradeLabelAsset; font.pixelSize: 11; font.weight: Font.Bold; color: Theme.textMuted }
                    ModernComboBox {
                        id: assetCombo
                        Layout.fillWidth: true
                        model: root.assetList
                        textRole: "symbol"
                        onActivated: root.refreshSuggestion()
                    }
                }

                // Miktar ve fiyat
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceMd

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        spacing: 4
                        Text { text: Strings.assetTradeLabelQty; font.pixelSize: 11; font.weight: Font.Bold; color: Theme.textMuted }
                        ModernInput {
                            id: qtyInput
                            Layout.fillWidth: true
                            implicitHeight: 38
                            font.family: Theme.monoFontFamily
                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                            onTextChanged: root.refreshFee()
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        spacing: 4
                        Text {
                            text: Strings.assetTradeLabelPrice + " (" + root.currency + ")"
                            font.pixelSize: 11
                            font.weight: Font.Bold
                            color: Theme.textMuted
                        }
                        ModernInput {
                            id: priceInput
                            Layout.fillWidth: true
                            implicitHeight: 38
                            font.family: Theme.monoFontFamily
                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                            onTextChanged: root.refreshFee()
                        }
                    }
                }

                // Kur (TRY fiyatlı varlıkta gizli)
                ColumnLayout {
                    visible: !root.isTry
                    Layout.fillWidth: true
                    spacing: 4
                    Text { text: Strings.assetTradeLabelFx; font.pixelSize: 11; font.weight: Font.Bold; color: Theme.textMuted }
                    ModernInput {
                        id: fxInput
                        Layout.fillWidth: true
                        implicitHeight: 38
                        font.family: Theme.monoFontFamily
                        inputMethodHints: Qt.ImhFormattedNumbersOnly
                    }
                }

                // Tarih ve saat
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

                // Tahmini tutar (varlığın para biriminde)
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
                            text: Strings.assetTradeTotal
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            color: Theme.textSecondary
                            Layout.fillWidth: true
                        }
                        Text {
                            text: root.totalValue.toLocaleString(Qt.locale("tr_TR"), "f", 2) + " " + root.currency
                            font.family: Theme.monoFontFamily
                            font.pixelSize: Theme.fontMd
                            font.weight: Font.Bold
                            color: root.isBuy ? Theme.bullGreen : Theme.bearRed
                        }
                    }
                }

                // Kullanılabilir nakit (ödeme para birimi) ve tahmini ücret
                Text {
                    visible: root.availableCash !== ""
                    text: Strings.assetTradeAvailableCash + root.availableCash
                    font.family: Theme.monoFontFamily
                    font.pixelSize: Theme.fontXs
                    color: Theme.textSecondary
                    Layout.fillWidth: true
                }

                Text {
                    visible: root.feeText !== ""
                    text: Strings.assetTradeEstimatedFee + root.feeText
                    font.family: Theme.monoFontFamily
                    font.pixelSize: Theme.fontXs
                    color: Theme.textSecondary
                    Layout.fillWidth: true
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
                        text: root.isBuy ? Strings.assetBuy : Strings.assetSell
                        variant: root.isBuy ? "primary" : "danger"
                        enabled: root.currentAssetId > 0
                        onClicked: assetsController.recordTrade(root.currentAssetId, {
                            "side": root.side, "quantity": qtyInput.text, "price": priceInput.text,
                            "date": dateInput.text.trim(), "time": timeInput.text.trim(),
                            "fx": root.isTry ? "" : fxInput.text
                        })
                    }
                }
            }
        }
    }
}
