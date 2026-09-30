import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

Popup {
    id: root

    property string movementType: "DEPOSIT" // "DEPOSIT" | "WITHDRAW"

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
        movementType = "DEPOSIT"
        txtAmount.text = "10000"
        txtNotes.text = ""
        var today = new Date()
        var yyyy = today.getFullYear()
        var mm = String(today.getMonth() + 1).padStart(2, '0')
        var dd = String(today.getDate()).padStart(2, '0')
        txtDate.text = yyyy + "-" + mm + "-" + dd
        var hh = String(today.getHours()).padStart(2, '0')
        var min = String(today.getMinutes()).padStart(2, '0')
        txtTime.text = hh + ":" + min
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
                iconSource: Icons.get("capital")
                iconColor: Theme.accent
                width: 20
                height: 20
            }

            Text {
                text: Strings.portfolioCapitalTitle
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

        // Nakit Bakiye Durumu
        Rectangle {
            Layout.fillWidth: true
            height: 32
            radius: Theme.radiusSm
            color: Theme.bgSecondary
            border.color: Theme.borderSubtle
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.spaceSm
                anchors.rightMargin: Theme.spaceSm

                ModernIcon {
                    iconSource: Icons.get("wallet")
                    iconColor: Theme.accent
                    width: 14
                    height: 14
                }

                Text {
                    text: Strings.portfolioKpiCash + ":"
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                }

                Text {
                    text: portfolioController.summaryRemainingCash
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    font.weight: Font.DemiBold
                    Layout.fillWidth: true
                }
            }
        }

        // Hareket Türü Seçici (Yatır / Çek)
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            Rectangle {
                Layout.fillWidth: true
                height: 38
                radius: Theme.radiusSm
                color: root.movementType === "DEPOSIT" ? Theme.bullGreen : Theme.bgSecondary
                border.color: root.movementType === "DEPOSIT" ? Theme.bullGreen : Theme.borderSubtle
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: Theme.spaceXs

                    ModernIcon {
                        iconSource: Icons.get("plus")
                        iconColor: root.movementType === "DEPOSIT" ? Theme.textInverse : Theme.bullGreen
                        width: 14
                        height: 14
                    }

                    Text {
                        text: Strings.portfolioCapitalDeposit
                        color: root.movementType === "DEPOSIT" ? Theme.textInverse : Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        font.weight: Font.DemiBold
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.movementType = "DEPOSIT"
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 38
                radius: Theme.radiusSm
                color: root.movementType === "WITHDRAW" ? Theme.bearRed : Theme.bgSecondary
                border.color: root.movementType === "WITHDRAW" ? Theme.bearRed : Theme.borderSubtle
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: Theme.spaceXs

                    ModernIcon {
                        iconSource: Icons.get("banknote")
                        iconColor: root.movementType === "WITHDRAW" ? Theme.textInverse : Theme.bearRed
                        width: 14
                        height: 14
                    }

                    Text {
                        text: Strings.portfolioCapitalWithdraw
                        color: root.movementType === "WITHDRAW" ? Theme.textInverse : Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        font.weight: Font.DemiBold
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.movementType = "WITHDRAW"
                }
            }
        }

        // Tutar Alanı
        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceXs

            Text {
                text: Strings.portfolioCapitalLabelAmount
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
            }

            TextField {
                id: txtAmount
                Layout.fillWidth: true
                placeholderText: "10000.00"
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

        // Tarih & Saat
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceMd

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceXs

                Text {
                    text: Strings.portfolioTradeLabelDate
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                }

                TextField {
                    id: txtDate
                    Layout.fillWidth: true
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    leftPadding: Theme.spaceSm
                    rightPadding: Theme.spaceSm

                    background: Rectangle {
                        color: Theme.bgInput
                        radius: Theme.radiusSm
                        border.color: txtDate.activeFocus ? Theme.borderFocus : Theme.borderSubtle
                        border.width: 1
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceXs

                Text {
                    text: Strings.portfolioTradeLabelTime
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                }

                TextField {
                    id: txtTime
                    Layout.fillWidth: true
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    leftPadding: Theme.spaceSm
                    rightPadding: Theme.spaceSm

                    background: Rectangle {
                        color: Theme.bgInput
                        radius: Theme.radiusSm
                        border.color: txtTime.activeFocus ? Theme.borderFocus : Theme.borderSubtle
                        border.width: 1
                    }
                }
            }
        }

        // Açıklama / Not
        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceXs

            Text {
                text: Strings.portfolioCapitalLabelNotes
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
            }

            TextField {
                id: txtNotes
                Layout.fillWidth: true
                placeholderText: Strings.portfolioCapitalPlaceholder
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBase
                leftPadding: Theme.spaceSm
                rightPadding: Theme.spaceSm

                background: Rectangle {
                    color: Theme.bgInput
                    radius: Theme.radiusSm
                    border.color: txtNotes.activeFocus ? Theme.borderFocus : Theme.borderSubtle
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
                width: 120
                height: 36
                radius: Theme.radiusSm
                color: btnConfirmMouse.containsMouse ? Theme.accentHover : Theme.accent

                Text {
                    anchors.centerIn: parent
                    text: Strings.btnSave
                    color: Theme.textInverse
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    font.weight: Font.DemiBold
                }

                MouseArea {
                    id: btnConfirmMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        var amt = parseFloat(txtAmount.text.replace(",", "."))
                        if (isNaN(amt) || amt <= 0) return

                        portfolioController.addCapitalMovement(
                            root.movementType,
                            amt,
                            txtDate.text.trim(),
                            txtTime.text.trim(),
                            txtNotes.text.trim()
                        )
                        root.close()
                    }
                }
            }
        }
    }
}
