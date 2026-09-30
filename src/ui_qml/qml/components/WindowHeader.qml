import QtQuick
import QtQuick.Layouts
import "../theme"

Rectangle {
    id: root

    property string title: Strings.appName
    signal searchRequested(string ticker)

    color: Theme.bgTitlebar
    implicitHeight: 48
    border.color: Theme.borderSubtle
    border.width: 1

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.spaceMd
        anchors.rightMargin: Theme.spaceMd
        spacing: Theme.spaceMd

        // Logo & Title
        Row {
            spacing: Theme.spaceSm
            Layout.alignment: Qt.AlignVCenter

            Rectangle {
                width: 28
                height: 28
                radius: Theme.radiusSm
                color: Theme.accent
                anchors.verticalCenter: parent.verticalCenter

                ModernIcon {
                    anchors.centerIn: parent
                    name: "barchart"
                    size: 16
                    color: "#ffffff"
                }
            }

            Text {
                text: root.title
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontMd
                font.weight: Font.Bold
                color: Theme.textPrimary
                font.letterSpacing: 0.5
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        Item { Layout.fillWidth: true } // Spacer

        // Quick Search Bar
        Rectangle {
            implicitWidth: 220
            implicitHeight: 30
            radius: Theme.radiusSm
            color: Theme.bgInput
            border.color: searchInput.activeFocus ? Theme.borderFocus : Theme.borderSubtle
            border.width: 1
            Layout.alignment: Qt.AlignVCenter

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                spacing: 6

                ModernIcon {
                    name: "search"
                    size: 13
                    color: Theme.textMuted
                }

                TextInput {
                    id: searchInput
                    Layout.fillWidth: true
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    color: Theme.textPrimary
                    selectByMouse: true
                    clip: true

                    Text {
                        text: Strings.searchPlaceholder
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        color: Theme.textMuted
                        visible: !searchInput.text && !searchInput.activeFocus
                    }

                    onAccepted: {
                        if (text.trim() !== "") {
                            root.searchRequested(text.trim().toUpperCase())
                        }
                    }
                }
            }
        }

        // BIST Session Status Badge
        Rectangle {
            implicitWidth: sessionRow.implicitWidth + 16
            implicitHeight: 26
            radius: Theme.radiusFull
            color: shellController.isBistOpen ? Theme.bullGreenSoft : Theme.bearRedSoft
            border.color: shellController.isBistOpen ? Theme.bullGreen : Theme.bearRed
            border.width: 1
            Layout.alignment: Qt.AlignVCenter

            Row {
                id: sessionRow
                anchors.centerIn: parent
                spacing: 6

                // Glowing pulsing indicator dot
                Rectangle {
                    width: 7
                    height: 7
                    radius: 4
                    color: shellController.isBistOpen ? Theme.bullGreen : Theme.bearRed
                    anchors.verticalCenter: parent.verticalCenter

                    SequentialAnimation on opacity {
                        running: shellController.isBistOpen
                        loops: Animation.Infinite
                        NumberAnimation { to: 0.3; duration: 800 }
                        NumberAnimation { to: 1.0; duration: 800 }
                    }
                }

                Text {
                    text: shellController.sessionText
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.DemiBold
                    color: shellController.isBistOpen ? Theme.bullGreen : Theme.bearRed
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }

        // Digital Clock
        Rectangle {
            implicitWidth: 80
            implicitHeight: 26
            radius: Theme.radiusSm
            color: Theme.bgInput
            Layout.alignment: Qt.AlignVCenter

            Text {
                anchors.centerIn: parent
                text: shellController.currentTime
                font.family: Theme.monoFontFamily
                font.pixelSize: Theme.fontSm
                font.weight: Font.Bold
                color: Theme.textSecondary
            }
        }

        // Theme Toggle Button
        Rectangle {
            implicitWidth: 30
            implicitHeight: 30
            radius: Theme.radiusSm
            color: themeBtnArea.containsMouse ? Theme.bgCardHover : "transparent"
            Layout.alignment: Qt.AlignVCenter

            ModernIcon {
                anchors.centerIn: parent
                name: Theme.isDark ? "sun" : "moon"
                size: 15
                color: Theme.textSecondary
            }

            MouseArea {
                id: themeBtnArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: Theme.isDark = !Theme.isDark
            }
        }
    }
}
