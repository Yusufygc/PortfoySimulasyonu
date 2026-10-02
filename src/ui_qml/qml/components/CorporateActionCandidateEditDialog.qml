import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// KAP/MKK kurumsal aksiyon adayını düzenleme diyaloğu.
Rectangle {
    id: root

    property bool isOpen: false
    property int candidateId: -1
    property string actionType: "BEDELSIZ"
    readonly property bool isBedelli: actionType === "BEDELLI"

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

    function open(candidate) {
        candidateId = candidate.id
        actionType = candidate.actionType
        txtTicker.text = candidate.ticker
        txtRatio.text = String(candidate.ratioPct)
        txtSubPrice.text = candidate.subscriptionPrice > 0 ? String(candidate.subscriptionPrice) : ""
        txtExDate.text = candidate.exDate
        txtNotes.text = candidate.notes
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
        width: Math.min(440, root.width - 32)
        implicitHeight: editColumn.implicitHeight + Theme.spaceLg * 2
        height: implicitHeight

        MouseArea { anchors.fill: parent }

        ColumnLayout {
            id: editColumn
            anchors.fill: parent
            anchors.margins: Theme.spaceLg
            spacing: Theme.spaceMd

            Text {
                text: Strings.caEditTitle
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontMd
                font.weight: Font.Bold
                color: Theme.textPrimary
                Layout.fillWidth: true
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceXs
                Text { text: Strings.caLabelTicker; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm }
                ModernInput { id: txtTicker; Layout.fillWidth: true }
            }

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
                    ModernInput { id: txtRatio; Layout.fillWidth: true; inputMethodHints: Qt.ImhFormattedNumbersOnly }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    visible: root.isBedelli
                    spacing: Theme.spaceXs
                    Text { text: Strings.caLabelSubPrice; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm; elide: Text.ElideRight; Layout.fillWidth: true }
                    ModernInput { id: txtSubPrice; Layout.fillWidth: true; inputMethodHints: Qt.ImhFormattedNumbersOnly }
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
                        corporateActionController.updateCandidate(
                            root.candidateId, txtTicker.text, root.actionType,
                            root.parseNumber(txtRatio.text), root.parseNumber(txtSubPrice.text),
                            txtExDate.text.trim(), txtNotes.text)
                        root.close()
                    }
                }
            }
        }
    }
}
