import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Karşılaştırma Laboratuvarı yapay zeka yorumu penceresi.
Rectangle {
    id: root

    property bool isOpen: false
    readonly property bool hasController: typeof comparisonController !== "undefined"
    readonly property bool busy: hasController && comparisonController.aiBusy
    readonly property string comment: hasController ? comparisonController.aiComment : ""

    anchors.fill: parent
    color: "#99000000"
    visible: opacity > 0
    opacity: isOpen ? 1.0 : 0.0
    z: 1000

    Behavior on opacity { NumberAnimation { duration: 180 } }

    function open() {
        isOpen = true
        if (hasController && comment === "" && !busy) comparisonController.generateAiComment()
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
        width: Math.min(760, root.width - 32)
        height: Math.min(root.height - 32, 620)

        MouseArea { anchors.fill: parent }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Theme.spaceLg
            spacing: Theme.spaceMd

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: Strings.compareAiTitle
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
                visible: root.busy
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                BusyIndicator { running: root.busy; implicitWidth: 24; implicitHeight: 24 }
                Text {
                    text: Strings.compareAiBusy
                    color: Theme.accent
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                }
            }

            Flickable {
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentWidth: width
                contentHeight: commentText.implicitHeight
                clip: true
                ScrollBar.vertical: ModernScrollBar {}

                Text {
                    id: commentText
                    width: parent.width
                    text: root.comment !== "" ? root.comment : (root.busy ? "" : Strings.compareAiEmpty)
                    textFormat: root.comment !== "" ? Text.MarkdownText : Text.PlainText
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    wrapMode: Text.WordWrap
                }
            }

            Text {
                text: Strings.compareAiDisclaimer
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Flow {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                layoutDirection: Qt.RightToLeft

                ModernButton {
                    text: Strings.btnClose
                    variant: "secondary"
                    onClicked: root.close()
                }
                ModernButton {
                    text: Strings.compareAiRegenerate
                    variant: "primary"
                    enabled: !root.busy
                    onClicked: comparisonController.generateAiComment()
                }
            }
        }
    }
}
