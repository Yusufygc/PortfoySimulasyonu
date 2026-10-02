import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Genel onay diyaloğu (yıkıcı işlemler için). Kullanım: dialog.ask(başlık, mesaj, onayMetni); onConfirmed: ...
Rectangle {
    id: root

    property bool isOpen: false
    property string title: ""
    property string message: ""
    property string confirmText: Strings.confirmDefault

    signal confirmed()

    anchors.fill: parent
    color: "#99000000"
    visible: opacity > 0
    opacity: isOpen ? 1.0 : 0.0
    z: 1100

    Behavior on opacity { NumberAnimation { duration: 160 } }

    function ask(dialogTitle, dialogMessage, dialogConfirmText) {
        title = dialogTitle
        message = dialogMessage
        confirmText = dialogConfirmText ? dialogConfirmText : Strings.confirmDefault
        isOpen = true
    }

    function close() {
        isOpen = false
    }

    MouseArea {
        anchors.fill: parent
        onClicked: root.close()
    }

    ModernCard {
        anchors.centerIn: parent
        width: Math.min(420, root.width - 32)
        implicitHeight: dialogColumn.implicitHeight + Theme.spaceLg * 2
        height: implicitHeight

        MouseArea { anchors.fill: parent }

        ColumnLayout {
            id: dialogColumn
            anchors.fill: parent
            anchors.margins: Theme.spaceLg
            spacing: Theme.spaceMd

            Text {
                text: root.title
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontMd
                font.weight: Font.Bold
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Text {
                text: root.message
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm

                Item { Layout.fillWidth: true }

                ModernButton {
                    text: Strings.confirmCancel
                    variant: "secondary"
                    onClicked: root.close()
                }
                ModernButton {
                    text: root.confirmText
                    variant: "danger"
                    onClicked: {
                        root.close()
                        root.confirmed()
                    }
                }
            }
        }
    }
}
