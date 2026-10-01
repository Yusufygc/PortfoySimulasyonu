import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

Popup {
    id: root

    property int goalId: 0
    property string goalName: ""
    property real targetAmount: 0.0
    property string deadline: ""
    property string priority: "MEDIUM"

    modal: true
    dim: true
    anchors.centerIn: Overlay.overlay
    width: Math.min(420, parent ? parent.width * 0.9 : 420)
    padding: Theme.spaceLg
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    background: Rectangle {
        color: Theme.bgCard
        radius: Theme.radiusMd
        border.color: Theme.borderCard
        border.width: 1
    }

    onOpened: {
        txtName.text = root.goalName
        txtTarget.text = root.targetAmount > 0 ? root.targetAmount.toString() : ""
        txtDeadline.text = root.deadline
        var p = (root.priority || "MEDIUM").toUpperCase()
        if (p === "HIGH" || p === "YÜKSEK") {
            comboPriority.currentIndex = 2
        } else if (p === "LOW" || p === "DÜŞÜK") {
            comboPriority.currentIndex = 0
        } else {
            comboPriority.currentIndex = 1
        }
        txtName.forceActiveFocus()
    }

    contentItem: ColumnLayout {
        spacing: Theme.spaceMd

        // Başlık
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            ModernIcon {
                name: "edit"
                color: Theme.accent
                size: 20
            }

            Text {
                text: Strings.goalsDialogEditTitle
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

        // Hedef Adı
        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceXs

            Text {
                text: Strings.goalsDialogNameLabel
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
            }

            TextField {
                id: txtName
                Layout.fillWidth: true
                placeholderText: "Örn: Ev Peşinatı / Yeni Araba"
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBase
                leftPadding: Theme.spaceSm
                rightPadding: Theme.spaceSm

                background: Rectangle {
                    color: Theme.bgInput
                    radius: Theme.radiusSm
                    border.color: txtName.activeFocus ? Theme.borderFocus : Theme.borderSubtle
                    border.width: 1
                }
            }
        }

        // Hedef Tutar
        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceXs

            Text {
                text: Strings.goalsDialogTargetLabel
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
            }

            TextField {
                id: txtTarget
                Layout.fillWidth: true
                placeholderText: "100000"
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBase
                leftPadding: Theme.spaceSm
                rightPadding: Theme.spaceSm
                inputMethodHints: Qt.ImhFormattedNumbersOnly

                background: Rectangle {
                    color: Theme.bgInput
                    radius: Theme.radiusSm
                    border.color: txtTarget.activeFocus ? Theme.borderFocus : Theme.borderSubtle
                    border.width: 1
                }
            }
        }

        // Hedef Tarih
        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceXs

            Text {
                text: Strings.goalsDialogDeadlineLabel + " (YYYY-AA-GG)"
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
            }

            TextField {
                id: txtDeadline
                Layout.fillWidth: true
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBase
                leftPadding: Theme.spaceSm
                rightPadding: Theme.spaceSm

                background: Rectangle {
                    color: Theme.bgInput
                    radius: Theme.radiusSm
                    border.color: txtDeadline.activeFocus ? Theme.borderFocus : Theme.borderSubtle
                    border.width: 1
                }
            }
        }

        // Öncelik
        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceXs

            Text {
                text: Strings.goalsDialogPriorityLabel
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
            }

            ComboBox {
                id: comboPriority
                Layout.fillWidth: true
                model: ["DÜŞÜK", "ORTA", "YÜKSEK"]

                background: Rectangle {
                    color: Theme.bgInput
                    radius: Theme.radiusSm
                    border.color: Theme.borderSubtle
                    border.width: 1
                }

                contentItem: Text {
                    leftPadding: Theme.spaceSm
                    text: comboPriority.displayText
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    verticalAlignment: Text.AlignVCenter
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
                width: 100
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
                width: 120
                height: 36
                radius: Theme.radiusSm
                color: btnSaveMouse.containsMouse ? Theme.accentHover : Theme.accent

                Text {
                    anchors.centerIn: parent
                    text: Strings.btnSave
                    color: Theme.textInverse
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
                        var name = txtName.text.trim()
                        var target = parseFloat(txtTarget.text.replace(",", "."))
                        var deadline = txtDeadline.text.trim()
                        if (!name || isNaN(target) || target <= 0 || !deadline) return

                        planningController.updateGoal(root.goalId, name, target, deadline, comboPriority.currentText)
                        root.close()
                    }
                }
            }

            Item { Layout.fillWidth: true }
        }
    }
}
