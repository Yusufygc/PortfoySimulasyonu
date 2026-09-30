import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

Popup {
    id: root

    property bool isEdit: false
    property int editPortfolioId: -1
    property string editName: ""
    property string editDesc: ""

    modal: true
    dim: true
    anchors.centerIn: Overlay.overlay
    width: Math.min(440, parent ? parent.width * 0.9 : 440)
    padding: 0
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    background: Rectangle {
        color: Theme.bgCard
        radius: Theme.radiusMd
        border.color: Theme.borderCard
        border.width: 1
    }

    onOpened: {
        if (isEdit) {
            txtName.text = editName
            txtDesc.text = editDesc
        } else {
            txtName.text = ""
            txtDesc.text = ""
            spinCash.value = 100000
        }
        txtName.forceActiveFocus()
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
                iconSource: Icons.get(root.isEdit ? "edit" : "plus")
                iconColor: Theme.accent
                width: 20
                height: 20
            }

            Text {
                text: root.isEdit ? Strings.portfolioEditTitle : Strings.portfolioNewTitle
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
                    iconSource: Icons.get("close")
                    iconColor: Theme.textMuted
                    width: 14
                    height: 14
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

        // Portföy Adı
        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceXs

            Text {
                text: Strings.portfolioLabelName
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
            }

            TextField {
                id: txtName
                Layout.fillWidth: true
                placeholderText: Strings.portfolioPlaceholderName
                maximumLength: 20
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBase
                leftPadding: Theme.spaceSm
                rightPadding: Theme.spaceSm
                topPadding: Theme.spaceSm
                bottomPadding: Theme.spaceSm

                background: Rectangle {
                    color: Theme.bgInput
                    radius: Theme.radiusSm
                    border.color: txtName.activeFocus ? Theme.borderFocus : Theme.borderSubtle
                    border.width: 1
                }
            }
        }

        // Açıklama
        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceXs

            Text {
                text: Strings.portfolioLabelDesc
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
            }

            TextField {
                id: txtDesc
                Layout.fillWidth: true
                placeholderText: Strings.portfolioPlaceholderDesc
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBase
                leftPadding: Theme.spaceSm
                rightPadding: Theme.spaceSm
                topPadding: Theme.spaceSm
                bottomPadding: Theme.spaceSm

                background: Rectangle {
                    color: Theme.bgInput
                    radius: Theme.radiusSm
                    border.color: txtDesc.activeFocus ? Theme.borderFocus : Theme.borderSubtle
                    border.width: 1
                }
            }
        }

        // Başlangıç Nakit (Sadece Yeni Oluştururken)
        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceXs
            visible: !root.isEdit

            Text {
                text: Strings.portfolioLabelCash
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
            }

            SpinBox {
                id: spinCash
                Layout.fillWidth: true
                from: 1000
                to: 100000000
                stepSize: 5000
                value: 100000
                editable: true

                contentItem: TextInput {
                    text: Number(spinCash.value).toLocaleString(Qt.locale("tr_TR")) + " ₺"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    color: Theme.textPrimary
                    horizontalAlignment: Qt.AlignLeft
                    verticalAlignment: Qt.AlignVCenter
                    leftPadding: Theme.spaceSm
                    readOnly: !spinCash.editable
                    validator: spinCash.validator
                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                }

                background: Rectangle {
                    color: Theme.bgInput
                    radius: Theme.radiusSm
                    border.color: spinCash.activeFocus ? Theme.borderFocus : Theme.borderSubtle
                    border.width: 1
                }
            }
        }

        Item { Layout.fillHeight: true }

        // Butonlar
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
                        if (txtName.text.trim() === "") return
                        if (root.isEdit) {
                            portfolioController.updatePortfolio(root.editPortfolioId, txtName.text, txtDesc.text)
                        } else {
                            portfolioController.createPortfolio(txtName.text, txtDesc.text, spinCash.value)
                        }
                        root.close()
                    }
                }
            }
        }
    }
}
