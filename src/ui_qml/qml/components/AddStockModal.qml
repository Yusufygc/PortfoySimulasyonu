import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

Rectangle {
    id: root

    property bool isOpen: false
    property int watchlistId: -1

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
        implicitHeight: 320
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
                    text: Strings.modalAddStockTitle
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontLg
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

            // Hisse Kodu
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                Text {
                    text: Strings.labelStock
                    font.family: Theme.fontFamily
                    font.pixelSize: 11
                    font.weight: Font.Bold
                    color: Theme.textMuted
                }
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
                        text: ""
                        font.family: Theme.monoFontFamily
                        font.pixelSize: Theme.fontBase
                        font.weight: Font.Bold
                        color: Theme.textPrimary
                    }
                }
            }

            // Not & Strateji
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
                    implicitHeight: 38
                    radius: Theme.radiusSm
                    color: Theme.bgInput
                    border.color: noteInput.activeFocus ? Theme.borderFocus : Theme.borderSubtle
                    border.width: 1

                    TextInput {
                        id: noteInput
                        anchors.fill: parent
                        anchors.margins: 10
                        text: ""
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        color: Theme.textPrimary
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
                    text: Strings.btnAddStockToWatchlist
                    iconName: "plus"
                    variant: "primary"
                    onClicked: {
                        if (watchlistController && root.watchlistId > 0) {
                            watchlistController.addStock(root.watchlistId, tickerInput.text, noteInput.text)
                        }
                        root.close()
                    }
                }
            }
        }
    }

    function open(wlId) {
        root.watchlistId = wlId || (watchlistController ? watchlistController.currentWatchlistId : -1)
        tickerInput.text = ""
        noteInput.text = ""
        root.isOpen = true
        tickerInput.forceActiveFocus()
    }

    function close() {
        root.isOpen = false
        root.closed()
    }
}
