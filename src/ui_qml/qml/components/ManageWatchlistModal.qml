import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

Rectangle {
    id: root

    property bool isOpen: false
    property string mode: "create" // "create" | "edit"
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
        width: 420
        implicitHeight: 330
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
                    text: root.mode === "create" ? Strings.modalNewWatchlistTitle : Strings.modalEditWatchlistTitle
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

            // Liste Adı
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                Text {
                    text: Strings.labelListName
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
                    border.color: nameInput.activeFocus ? Theme.borderFocus : Theme.borderSubtle
                    border.width: 1

                    TextInput {
                        id: nameInput
                        anchors.fill: parent
                        anchors.margins: 10
                        text: ""
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        font.weight: Font.DemiBold
                        color: Theme.textPrimary
                    }
                }
            }

            // Açıklama
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                Text {
                    text: Strings.labelListDesc
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
                    border.color: descInput.activeFocus ? Theme.borderFocus : Theme.borderSubtle
                    border.width: 1

                    TextInput {
                        id: descInput
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
                    text: Strings.btnSave
                    variant: "primary"
                    onClicked: {
                        if (watchlistController) {
                            if (root.mode === "create") {
                                watchlistController.createWatchlist(nameInput.text, descInput.text)
                            } else {
                                watchlistController.updateWatchlist(root.watchlistId, nameInput.text, descInput.text)
                            }
                        }
                        root.close()
                    }
                }
            }
        }
    }

    function openCreate() {
        root.mode = "create"
        root.watchlistId = -1
        nameInput.text = ""
        descInput.text = ""
        root.isOpen = true
        nameInput.forceActiveFocus()
    }

    function openEdit(wlId, currentName, currentDesc) {
        root.mode = "edit"
        root.watchlistId = wlId
        nameInput.text = currentName || ""
        descInput.text = currentDesc || ""
        root.isOpen = true
        nameInput.forceActiveFocus()
    }

    function close() {
        root.isOpen = false
        root.closed()
    }
}
