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
    padding: Theme.spaceLg
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

    contentItem: ColumnLayout {
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

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.borderSubtle
        }

        // Hedef Bilgisi
        Rectangle {
            Layout.fillWidth: true
            height: 48
            radius: Theme.radiusSm
            color: Theme.bgSecondary

            RowLayout {
                anchors.fill: parent
                anchors.margins: Theme.spaceSm
                spacing: Theme.spaceSm

                Text {
                    text: root.goalName
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    font.weight: Font.DemiBold
                    Layout.fillWidth: true
                }

                Text {
                    text: Strings.goalRemainingPrefix + root.remainingFormatted
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

        // Alt Butonlar (Düzeltildi ve Ortalandı)
        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: Theme.spaceSm
            spacing: Theme.spaceMd

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
                    text: Strings.btnSave
                    color: btnSaveMouse.containsMouse ? Theme.textInverse : Theme.bullGreen
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
                        var amount = parseFloat(txtAmount.text.replace(",", "."))
                        if (isNaN(amount) || amount <= 0 || root.goalId < 0) return

                        planningController.addContribution(root.goalId, amount)
                        root.close()
                    }
                }
            }

            Item { Layout.fillWidth: true }
        }
    }
}
