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
    width: Math.min(460, parent ? parent.width * 0.9 : 460)
    padding: Theme.spaceLg
    contentHeight: contentCol.implicitHeight
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
            txtCash.text = "100000"
        }
        txtName.forceActiveFocus()
    }

    ColumnLayout {
        id: contentCol
        width: parent.width
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

            Rectangle {
                Layout.fillWidth: true
                height: 42
                color: Theme.bgInput
                radius: Theme.radiusSm
                border.color: txtCash.activeFocus ? Theme.borderFocus : Theme.borderSubtle
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.spaceSm
                    anchors.rightMargin: Theme.spaceSm
                    spacing: Theme.spaceXs

                    TextField {
                        id: txtCash
                        Layout.fillWidth: true
                        text: "100000"
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        inputMethodHints: Qt.ImhFormattedNumbersOnly
                        background: null
                        leftPadding: 0
                        rightPadding: 0
                    }

                    Text {
                        text: "₺"
                        color: Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        font.weight: Font.Bold
                    }
                }
            }
        }

        Item { Layout.preferredHeight: Theme.spaceSm }

        // Butonlar (Ortalanmış)
        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: Theme.spaceMd

            Rectangle {
                width: 110
                height: 38
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
                width: 130
                height: 38
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
                            var initialCash = parseFloat(txtCash.text.replace(",", ".")) || 100000.0
                            portfolioController.createPortfolio(txtName.text, txtDesc.text, initialCash)
                        }
                        root.close()
                    }
                }
            }
        }
    }
}
