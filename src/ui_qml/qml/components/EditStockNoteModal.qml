import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

Rectangle {
    id: root

    property bool isOpen: false
    property int watchlistId: -1
    property int stockId: -1
    property string ticker: ""

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
        width: 400
        implicitHeight: 280
        scale: root.isOpen ? 1.0 : 0.95

        Behavior on scale { NumberAnimation { duration: 200; easing.type: Easing.OutBack } }

        MouseArea {
            anchors.fill: parent
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Theme.spaceLg
            spacing: Theme.spaceMd

            // Başlık & Kapat Butonu
            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: root.ticker !== "" ? (root.ticker + " — " + Strings.modalEditNoteTitle) : Strings.modalEditNoteTitle
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontMd
                    font.weight: Font.Bold
                    color: Theme.textPrimary
                    Layout.fillWidth: true
                }
                Item {
                    width: 24
                    height: 24
                    ModernIcon {
                        name: "close"
                        size: 16
                        color: Theme.textMuted
                        anchors.centerIn: parent
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.close()
                    }
                }
            }

            // Not & Strateji Girişi
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                Text {
                    text: Strings.labelStockNotes
                    font.family: Theme.fontFamily
                    font.pixelSize: 11
                    font.weight: Font.Bold
                    color: Theme.textMuted
                }
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 70
                    radius: Theme.radiusSm
                    color: Theme.bgInput
                    border.color: noteInput.activeFocus ? Theme.borderFocus : Theme.borderSubtle
                    border.width: 1

                    TextArea {
                        id: noteInput
                        anchors.fill: parent
                        anchors.margins: 8
                        text: ""
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        color: Theme.textPrimary
                        wrapMode: TextEdit.WordWrap
                    }
                }
            }

            Item { Layout.fillHeight: true }

            // Butonlar
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
                    text: Strings.btnSave
                    variant: "primary"
                    onClicked: {
                        if (watchlistController && root.watchlistId > 0 && root.stockId > 0) {
                            watchlistController.updateStockNotes(root.watchlistId, root.stockId, noteInput.text)
                        }
                        root.close()
                    }
                }
            }
        }
    }

    function open(wlId, sId, tickerSym, currentNote) {
        root.watchlistId = wlId
        root.stockId = sId
        root.ticker = tickerSym || ""
        noteInput.text = currentNote || ""
        root.isOpen = true
        noteInput.forceActiveFocus()
    }

    function close() {
        root.isOpen = false
        root.closed()
    }
}
