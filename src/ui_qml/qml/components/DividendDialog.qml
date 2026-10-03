import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Nakit temettü kaydı ve geçmişi diyaloğu (ana portföy pozisyonu için).
Rectangle {
    id: root

    property bool isOpen: false
    property string ticker: ""
    property string statusText: ""
    property bool statusIsError: false
    readonly property var ctl: (typeof dividendController !== "undefined") ? dividendController : null
    readonly property bool hasDividends: ctl ? ctl.hasDividends : false

    // Temettü kaydedildiğinde veya silindiğinde yayınlanır (ebeveyn verileri yenileyebilir)
    signal dividendsUpdated(string message)

    anchors.fill: parent
    color: "#99000000"
    visible: opacity > 0
    opacity: isOpen ? 1.0 : 0.0
    z: 1000

    Behavior on opacity { NumberAnimation { duration: 180 } }

    function todayIso() {
        const d = new Date()
        return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0")
    }

    function open(tickerSym) {
        ticker = tickerSym || ""
        if (ctl) {
            ctl.loadFor(ticker)
        }
        txtAmount.text = ""
        txtDate.text = todayIso()
        txtNote.text = ""
        statusText = ""
        isOpen = true
    }

    function close() {
        isOpen = false
    }

    Connections {
        target: root.ctl
        function onNotification(success, message) {
            if (!root.isOpen) return
            root.statusText = message
            root.statusIsError = !success
            if (success) {
                txtAmount.text = ""
                txtNote.text = ""
                root.dividendsUpdated(message)
            }
        }
    }

    MouseArea {
        anchors.fill: parent
        onClicked: root.close()
    }

    ModernCard {
        anchors.centerIn: parent
        width: Math.min(460, root.width - 32)
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
                        text: root.ticker !== "" ? (root.ticker + " — " + Strings.dividendTitle) : Strings.dividendTitle
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

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceSm

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceXs
                        Text { text: Strings.dividendLabelAmount; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm; elide: Text.ElideRight; Layout.fillWidth: true }
                        ModernInput {
                            id: txtAmount
                            Layout.fillWidth: true
                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceXs
                        Text { text: Strings.dividendLabelDate; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm; elide: Text.ElideRight; Layout.fillWidth: true }
                        ModernInput { id: txtDate; Layout.fillWidth: true }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceXs
                    Text { text: Strings.dividendLabelNote; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm }
                    ModernInput { id: txtNote; Layout.fillWidth: true }
                }

                Text {
                    text: Strings.dividendInfoNote
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

                ModernButton {
                    Layout.fillWidth: true
                    text: Strings.dividendBtnAdd
                    variant: "primary"
                    enabled: root.ctl !== null
                    onClicked: {
                        root.statusText = ""
                        root.ctl.addDividend(txtAmount.text, txtDate.text.trim(), txtNote.text)
                    }
                }

                // Geçmiş
                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: Strings.dividendHistoryTitle
                        color: Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        font.weight: Font.Bold
                        Layout.fillWidth: true
                    }
                    Text {
                        visible: root.hasDividends
                        text: Strings.dividendTotalLabel + ": " + (root.ctl ? root.ctl.totalText : "")
                        color: Theme.bullGreen
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontSm
                        font.weight: Font.DemiBold
                    }
                }

                Text {
                    visible: !root.hasDividends
                    text: Strings.dividendEmpty
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    Layout.fillWidth: true
                }

                Repeater {
                    model: root.ctl ? root.ctl.dividends : []

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: rowLayout.implicitHeight + Theme.spaceSm * 2
                        radius: Theme.radiusSm
                        color: Theme.bgSecondary
                        border.color: Theme.borderSubtle

                        RowLayout {
                            id: rowLayout
                            anchors.fill: parent
                            anchors.margins: Theme.spaceSm
                            spacing: Theme.spaceMd

                            Text {
                                text: modelData.dateText
                                color: Theme.textSecondary
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSm
                            }
                            Text {
                                text: modelData.note
                                color: Theme.textMuted
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSm
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                            Text {
                                text: modelData.amountText
                                color: Theme.textPrimary
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSm
                                font.weight: Font.DemiBold
                            }
                            Item {
                                width: 24
                                height: 24
                                ModernIcon { name: "trash"; size: 14; color: Theme.textMuted; anchors.centerIn: parent }
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    hoverEnabled: true
                                    ToolTip.visible: containsMouse
                                    ToolTip.text: Strings.dividendDeleteTooltip
                                    onClicked: root.ctl.deleteDividend(modelData.id)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
