import QtQuick
import QtQuick.Layouts
import "../theme"

Rectangle {
    id: root

    property bool isCollapsed: false
    signal itemClicked(int index)

    color: Theme.bgSidebar
    implicitWidth: isCollapsed ? 64 : 210
    border.color: Theme.borderSubtle
    border.width: 1

    Behavior on implicitWidth {
        NumberAnimation { duration: 180; easing.type: Easing.OutCubic }
    }

    readonly property var menuItems: [
        { index: 0, title: "Genel Bakış",       icon: "📊" },
        { index: 1, title: "İzleme Listeleri",   icon: "⭐" },
        { index: 2, title: "Model Portföyler",   icon: "💼" },
        { index: 3, title: "Hisse 360",          icon: "🎯" },
        { index: 4, title: "Karşılaştırma Lab",  icon: "⚖️" },
        { index: 5, title: "Hisse Tarayıcı",     icon: "🔍" },
        { index: 6, title: "Finansal Planlama",  icon: "📅" },
        { index: 7, title: "Optimizasyon",       icon: "🛡️" },
        { index: 8, title: "AI Asistan",         icon: "🤖" },
        { index: 9, title: "Ayarlar",            icon: "⚙️" },
    ]

    ColumnLayout {
        anchors.fill: parent
        anchors.topMargin: Theme.spaceSm
        anchors.bottomMargin: Theme.spaceSm
        spacing: 2

        // Collapse / Expand toggle button
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 36
            color: collapseMouse.containsMouse ? Theme.bgCardHover : "transparent"
            radius: Theme.radiusSm

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 18
                anchors.rightMargin: 12
                spacing: 12

                Text {
                    text: root.isCollapsed ? "➡️" : "⬅️"
                    font.pixelSize: 13
                    Layout.alignment: Qt.AlignVCenter
                }

                Text {
                    visible: !root.isCollapsed
                    text: "Menüyü Daralt"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    color: Theme.textMuted
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                    Layout.alignment: Qt.AlignVCenter
                }
            }

            MouseArea {
                id: collapseMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.isCollapsed = !root.isCollapsed
            }
        }

        // Separator
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            Layout.topMargin: 4
            Layout.bottomMargin: 4
            color: Theme.borderSubtle
        }

        // Navigation Items
        Repeater {
            model: root.menuItems

            Rectangle {
                id: navItem
                Layout.fillWidth: true
                Layout.preferredHeight: 40
                radius: Theme.radiusSm

                readonly property bool isActive: shellController.activePage === modelData.index
                readonly property bool isHovered: itemMouse.containsMouse

                color: {
                    if (isActive) return Theme.accentSoft
                    if (isHovered) return Theme.bgCardHover
                    return "transparent"
                }

                Behavior on color { ColorAnimation { duration: 120 } }

                // Active Glowing Indicator Strip on the left
                Rectangle {
                    width: 3
                    height: 22
                    radius: 2
                    color: Theme.accent
                    anchors.left: parent.left
                    anchors.leftMargin: 3
                    anchors.verticalCenter: parent.verticalCenter
                    visible: navItem.isActive
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 18
                    anchors.rightMargin: 12
                    spacing: 12

                    Text {
                        text: modelData.icon
                        font.pixelSize: 15
                        Layout.alignment: Qt.AlignVCenter
                    }

                    Text {
                        visible: !root.isCollapsed
                        text: modelData.title
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        font.weight: navItem.isActive ? Font.Bold : Font.Normal
                        color: navItem.isActive ? Theme.accent : (navItem.isHovered ? Theme.textPrimary : Theme.textSecondary)
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                        Layout.alignment: Qt.AlignVCenter

                        Behavior on color { ColorAnimation { duration: 120 } }
                    }
                }

                MouseArea {
                    id: itemMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        shellController.navigateTo(modelData.index)
                        root.itemClicked(modelData.index)
                    }
                }
            }
        }

        Item { Layout.fillHeight: true } // Spacer
    }
}
