import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

Popup {
    id: root

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
        txtName.text = ""
        txtTarget.text = "100000"
        var d = new Date()
        d.setFullYear(d.getFullYear() + 1)
        var yyyy = d.getFullYear()
        var mm = String(d.getMonth() + 1).padStart(2, '0')
        var dd = String(d.getDate()).padStart(2, '0')
        txtDeadline.text = yyyy + "-" + mm + "-" + dd
        comboPriority.currentIndex = 1 // ORTA
        txtName.forceActiveFocus()
    }

    contentItem: ColumnLayout {
        spacing: Theme.spaceMd

        // Başlık
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            ModernIcon {
                name: "target"
                color: Theme.accent
                size: 20
            }

            Text {
                text: Strings.goalsDialogNewTitle
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
                placeholderText: Strings.goalNamePlaceholder
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

                        planningController.addGoal(name, target, deadline, comboPriority.currentText)
                        root.close()
                    }
                }
            }

            Item { Layout.fillWidth: true }
        }
    }
}
