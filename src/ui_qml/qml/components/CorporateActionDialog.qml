import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Bedelli / bedelsiz sermaye artırımı giriş ve ön izleme diyaloğu (ana portföy pozisyonu için).
Rectangle {
    id: root

    property bool isOpen: false
    property string ticker: ""
    property var ctx: ({ found: false, quantity: 0, avgCost: 0, totalCost: 0, currentPrice: 0 })
    property string actionType: "BEDELSIZ"
    property var preview: ({ valid: false })
    property string statusText: ""
    property bool statusIsError: false

    readonly property bool isBedelli: actionType === "BEDELLI"
    readonly property bool busy: (typeof corporateActionController !== "undefined") && corporateActionController.isBusy

    // İşlem başarıyla uygulandığında yayınlanır (ebeveyn toast gösterebilir)
    signal applied(string message)

    anchors.fill: parent
    color: "#99000000"
    visible: opacity > 0
    opacity: isOpen ? 1.0 : 0.0
    z: 1000

    Behavior on opacity { NumberAnimation { duration: 180 } }

    function parseNumber(text) {
        const n = Number(String(text).replace(",", "."))
        return isNaN(n) ? 0 : n
    }

    function refreshPreview() {
        if (typeof corporateActionController === "undefined" || !ctx.found) {
            preview = { valid: false }
            return
        }
        preview = corporateActionController.computePreview(
            ctx.quantity, ctx.totalCost, ctx.currentPrice, actionType,
            parseNumber(txtRatio.text), parseNumber(txtSubPrice.text))
    }

    function todayIso() {
        const d = new Date()
        return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0")
    }

    function open(tickerSym) {
        ticker = tickerSym || ""
        ctx = (typeof corporateActionController !== "undefined")
              ? corporateActionController.loadContext(ticker)
              : { found: false, quantity: 0, avgCost: 0, totalCost: 0, currentPrice: 0 }
        actionType = "BEDELSIZ"
        txtRatio.text = "50"
        txtExDate.text = todayIso()
        txtSubPrice.text = "1"
        txtNotes.text = ""
        statusText = ctx.found ? "" : Strings.caNoPosition
        statusIsError = !ctx.found
        refreshPreview()
        isOpen = true
    }

    function close() {
        isOpen = false
    }

    onActionTypeChanged: refreshPreview()

    Connections {
        target: (typeof corporateActionController !== "undefined") ? corporateActionController : null
        function onNotification(success, message) {
            if (!root.isOpen) return
            if (success) {
                root.close()
                root.applied(message)
            } else {
                root.statusText = message
                root.statusIsError = true
            }
        }
    }

    MouseArea {
        anchors.fill: parent
        onClicked: root.close()
    }

    ModernCard {
        anchors.centerIn: parent
        width: Math.min(480, root.width - 32)
        implicitHeight: Math.min(root.height - 32, formColumn.implicitHeight + Theme.spaceLg * 2)
        height: implicitHeight
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

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: root.ticker !== "" ? (root.ticker + " — " + Strings.caTitle) : Strings.caTitle
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontMd
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

                // Pozisyon özeti
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: infoRow.implicitHeight + Theme.spaceMd
                    radius: Theme.radiusSm
                    color: Theme.bgSecondary
                    border.color: Theme.borderSubtle

                    RowLayout {
                        id: infoRow
                        anchors.fill: parent
                        anchors.margins: Theme.spaceSm
                        spacing: Theme.spaceLg

                        Repeater {
                            model: [
                                { label: Strings.caCurrentLot, value: Number(root.ctx.quantity).toLocaleString(Qt.locale("tr_TR"), "f", 0) },
                                { label: Strings.caAvgCost, value: Number(root.ctx.avgCost).toLocaleString(Qt.locale("tr_TR"), "f", 4) + " ₺" },
                                { label: Strings.caCurrentPrice, value: root.ctx.currentPrice > 0 ? Number(root.ctx.currentPrice).toLocaleString(Qt.locale("tr_TR"), "f", 4) + " ₺" : "-" }
                            ]
                            ColumnLayout {
                                spacing: 2
                                Text { text: modelData.label; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.Bold }
                                Text { text: modelData.value; color: Theme.textPrimary; font.family: Theme.fontMono; font.pixelSize: Theme.fontBase; font.weight: Font.DemiBold }
                            }
                        }
                        Item { Layout.fillWidth: true }
                    }
                }

                // İşlem türü
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceXs
                    Text { text: Strings.caLabelType; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm }
                    RowLayout {
                        spacing: Theme.spaceSm
                        ModernButton {
                            text: Strings.caTypeBedelsiz
                            variant: root.actionType === "BEDELSIZ" ? "primary" : "secondary"
                            onClicked: root.actionType = "BEDELSIZ"
                        }
                        ModernButton {
                            text: Strings.caTypeBedelli
                            variant: root.actionType === "BEDELLI" ? "primary" : "secondary"
                            onClicked: root.actionType = "BEDELLI"
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceSm

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceXs
                        Text { text: Strings.caLabelRatio; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm }
                        ModernInput {
                            id: txtRatio
                            Layout.fillWidth: true
                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                            onTextChanged: root.refreshPreview()
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        visible: root.isBedelli
                        spacing: Theme.spaceXs
                        Text { text: Strings.caLabelSubPrice; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm; elide: Text.ElideRight; Layout.fillWidth: true }
                        ModernInput {
                            id: txtSubPrice
                            Layout.fillWidth: true
                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                            onTextChanged: root.refreshPreview()
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceXs
                    Text { text: Strings.caLabelExDate; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm }
                    ModernInput { id: txtExDate; Layout.fillWidth: true }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceXs
                    Text { text: Strings.caLabelNotes; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm }
                    ModernInput { id: txtNotes; Layout.fillWidth: true }
                }

                // Ön izleme
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: previewCol.implicitHeight + Theme.spaceMd
                    radius: Theme.radiusSm
                    color: Theme.bgSecondary
                    border.color: Theme.borderSubtle

                    ColumnLayout {
                        id: previewCol
                        anchors.fill: parent
                        anchors.margins: Theme.spaceSm
                        spacing: 4

                        Text { text: Strings.caPreviewTitle; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.Bold }

                        Repeater {
                            model: [
                                { label: Strings.caPreviewNewShares, value: root.preview.valid ? root.preview.newShareText : "-", show: true },
                                { label: Strings.caPreviewTotalLot, value: root.preview.valid ? root.preview.totalQtyText : "-", show: true },
                                { label: Strings.caPreviewNewAvg, value: root.preview.valid ? root.preview.newAvgText : "-", show: true },
                                { label: Strings.caPreviewCapital, value: root.preview.valid ? root.preview.capitalText : "-", show: root.isBedelli },
                                { label: Strings.caPreviewTheoretical, value: root.preview.valid ? root.preview.theoreticalText : "-", show: true }
                            ]
                            RowLayout {
                                Layout.fillWidth: true
                                visible: modelData.show
                                Text { text: modelData.label; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm; Layout.fillWidth: true }
                                Text { text: modelData.value; color: Theme.textPrimary; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; font.weight: Font.DemiBold }
                            }
                        }

                        Text {
                            visible: root.ctx.found && !root.preview.valid
                            text: Strings.caInsufficientLots
                            color: Theme.warning
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }
                }

                Text {
                    text: Strings.caRetroNote
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                Text {
                    visible: root.statusText !== ""
                    text: root.statusText
                    color: root.statusIsError ? Theme.bearRed : Theme.bullGreen
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceSm

                    ModernButton {
                        Layout.fillWidth: true
                        text: Strings.btnCancel
                        variant: "secondary"
                        onClicked: root.close()
                    }
                    ModernButton {
                        Layout.fillWidth: true
                        text: Strings.caBtnApply
                        variant: "primary"
                        enabled: root.ctx.found && root.preview.valid && !root.busy
                        onClicked: {
                            root.statusText = ""
                            corporateActionController.applyAction(
                                root.ticker, root.actionType, root.parseNumber(txtRatio.text),
                                txtExDate.text.trim(), root.parseNumber(txtSubPrice.text), txtNotes.text)
                        }
                    }
                }
            }
        }
    }
}
