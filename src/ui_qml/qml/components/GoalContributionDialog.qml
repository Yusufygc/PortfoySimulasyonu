import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

Popup {
    id: root

    property int goalId: -1
    property string goalName: ""
    property string remainingFormatted: ""

    modal: true
    dim: true
    anchors.centerIn: Overlay.overlay
    width: Math.min(380, parent ? parent.width * 0.9 : 380)
    padding: 0
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    background: Rectangle {
        color: Theme.bgCard
        radius: Theme.radiusMd
        border.color: Theme.borderCard
        border.width: 1
    }

    onOpened: {
        txtAmount.text = "5000"
        txtAmount.forceActiveFocus()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spaceLg
        spacing: Theme.spaceMd

        // Başlık
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            ModernIcon {
                name: "coins"
                color: Theme.bullGreen
                size: 20
            }

            Text {
                text: Strings.goalsDialogContributeTitle
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontLg
                font.weight: Font.DemiBold
                Layout.fillWidth: true
            }

            Rectangle {
                width: 28
                height: 28
                radius: Theme.radiusSm
                color: closeMouseArea.containsMouse ? Theme.bgCardHover : "transparent"

                ModernIcon {
                    anchors.centerIn: parent
                    name: "close"
                    color: Theme.textMuted
                    size: 14
                }

                MouseArea {
                    id: closeMouseArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.close()
                }
            }
        }

        // Hedef Bilgisi
        Rectangle {
            Layout.fillWidth: true
            height: 48
            radius: Theme.radiusSm
            color: Theme.bgSecondary
            border.color: Theme.borderSubtle
            border.width: 1

            ColumnLayout {
                anchors.centerIn: parent
                spacing: 2

                Text {
                    text: root.goalName
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    font.weight: Font.Bold
                }

                Text {
                    text: "Kalan Hedef: " + root.remainingFormatted
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                }
            }
        }

        // Katkı Tutarı
        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceXs

            Text {
                text: Strings.goalsDialogContributeAmountLabel
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
            }

            TextField {
                id: txtAmount
                Layout.fillWidth: true
                placeholderText: "5000"
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBase
                leftPadding: Theme.spaceSm
                rightPadding: Theme.spaceSm
                inputMethodHints: Qt.ImhFormattedNumbersOnly

                background: Rectangle {
                    color: Theme.bgInput
                    radius: Theme.radiusSm
                    border.color: txtAmount.activeFocus ? Theme.borderFocus : Theme.borderSubtle
                    border.width: 1
                }
            }
        }

        Item { Layout.fillHeight: true }

        // Alt Butonlar
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            Item { Layout.fillWidth: true }

            Rectangle {
                width: 90
                height: 36
                radius: Theme.radiusSm
                color: btnCancelMouse.containsMouse ? Theme.bgCardHover : "transparent"
                border.color: Theme.borderSubtle
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: Strings.btnCancel
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                }

                MouseArea {
                    id: btnCancelMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.close()
                }
            }

            Rectangle {
                width: 110
                height: 36
                radius: Theme.radiusSm
                color: btnSaveMouse.containsMouse ? Theme.bullGreen : Theme.bullGreenSoft

                Text {
                    anchors.centerIn: parent
                    text: Strings.goalsBtnContribute
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    font.weight: Font.DemiBold
                }

                MouseArea {
                    id: btnSaveMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        var amt = parseFloat(txtAmount.text.replace(",", "."))
                        if (isNaN(amt) || amt <= 0 || root.goalId < 0) return

                        planningController.addContribution(root.goalId, amt)
                        root.close()
                    }
                }
            }
        }
    }
}
