import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    id: root

    property int activeTab: 0

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spaceMd

        // Başlık + sekme seçici (dar pencerede sekmeler alta sarar)
        Flow {
            Layout.fillWidth: true
            spacing: Theme.spaceMd

            ColumnLayout {
                spacing: 2

                Text {
                    text: Strings.screenerTitle
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXl
                    font.weight: Font.Bold
                }

                Text {
                    text: Strings.screenerSubtitle
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                }
            }

            Rectangle {
                height: 38
                width: tabRow.implicitWidth + 8
                radius: Theme.radiusMd
                color: Theme.bgSecondary
                border.color: Theme.borderSubtle
                border.width: 1

                Row {
                    id: tabRow
                    anchors.centerIn: parent
                    spacing: 4

                    Repeater {
                        model: [Strings.screenerTabStrategies, Strings.screenerTabGoldenCross]

                        Rectangle {
                            height: 30
                            width: tabLabel.implicitWidth + 24
                            radius: Theme.radiusSm
                            color: root.activeTab === index ? Theme.primary : (tabMouse.containsMouse ? Theme.bgCardHover : "transparent")

                            Text {
                                id: tabLabel
                                anchors.centerIn: parent
                                text: modelData
                                color: root.activeTab === index ? "#FFFFFF" : Theme.textSecondary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                font.weight: root.activeTab === index ? Font.DemiBold : Font.Normal
                            }

                            MouseArea {
                                id: tabMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.activeTab = index
                            }
                        }
                    }
                }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.activeTab

            ScreenerStrategiesTab {}

            GoldenCrossTab {
                onNotify: function(success, message) { screenerToast.show(message, success) }
            }
        }
    }

    ToastNotification {
        id: screenerToast
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 24
        z: 999
    }
}
