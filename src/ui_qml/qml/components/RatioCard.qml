import QtQuick
import QtQuick.Layouts
import "../theme"

Rectangle {
    id: root

    property string title: ""
    property string value: "—"
    property string subtitle: ""
    property string iconName: "trending-up"
    property color accentColor: Theme.accent
    property string badgeText: ""

    implicitWidth: 160
    implicitHeight: 96
    Layout.fillWidth: true
    Layout.minimumWidth: 130
    Layout.preferredHeight: 96

    radius: Theme.radiusMd
    color: Theme.bgCard
    border.color: hoverArea.containsMouse ? Theme.borderStrong : Theme.borderSubtle
    border.width: 1

    Behavior on border.color {
        ColorAnimation { duration: 150 }
    }

    MouseArea {
        id: hoverArea
        anchors.fill: parent
        hoverEnabled: true
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spaceSm
        spacing: 4

        // Top Row: Title, Icon, Badge
        RowLayout {
            Layout.fillWidth: true
            spacing: 6

            // Accent Pill Indicator / Icon
            Rectangle {
                width: 22
                height: 22
                radius: Theme.radiusSm
                color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.12)
                Layout.alignment: Qt.AlignVCenter

                ModernIcon {
                    anchors.centerIn: parent
                    name: root.iconName
                    size: 13
                    color: root.accentColor
                }
            }

            Text {
                text: root.title
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                font.weight: Font.DemiBold
                color: Theme.textSecondary
                elide: Text.ElideRight
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter
            }

            // Optional Badge
            Rectangle {
                visible: root.badgeText !== ""
                implicitWidth: badgeLabel.implicitWidth + 8
                implicitHeight: 18
                radius: 9
                color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.15)
                Layout.alignment: Qt.AlignVCenter

                Text {
                    id: badgeLabel
                    anchors.centerIn: parent
                    text: root.badgeText
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.Medium
                    color: root.accentColor
                }
            }
        }

        // Value
        Text {
            text: root.value
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontLg
            font.weight: Font.Bold
            color: Theme.textPrimary
            elide: Text.ElideRight
            Layout.fillWidth: true
        }

        // Subtitle
        Text {
            text: root.subtitle
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontXs
            color: Theme.textMuted
            elide: Text.ElideRight
            Layout.fillWidth: true
        }
    }
}
