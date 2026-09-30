import QtQuick
import QtQuick.Layouts
import "../theme"

ModernCard {
    id: root

    property string title: "Metrik Başlığı"
    property string value: "₺0,00"
    property string changeText: "+0.00%"
    property bool isPositive: true
    property string subText: Strings.subtextLastUpdate
    property string iconName: ""
    property string iconSymbol: ""

    hoverable: true
    implicitWidth: 240
    implicitHeight: 110

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spaceMd
        spacing: Theme.spaceXs

        RowLayout {
            Layout.fillWidth: true

            Text {
                text: root.title
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                font.weight: Font.DemiBold
                color: Theme.textSecondary
                Layout.fillWidth: true
                elide: Text.ElideRight
            }

            ModernIcon {
                visible: root.iconName !== ""
                name: root.iconName
                size: 16
                color: Theme.textMuted
            }

            Text {
                visible: root.iconName === "" && root.iconSymbol !== ""
                text: root.iconSymbol
                font.pixelSize: 14
                color: Theme.textMuted
            }
        }

        Text {
            text: root.value
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontXl
            font.weight: Font.Bold
            color: Theme.textPrimary
            elide: Text.ElideRight
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            // Pill Badge
            Rectangle {
                implicitWidth: badgeText.implicitWidth + 12
                implicitHeight: 20
                radius: Theme.radiusFull
                color: root.isPositive ? Theme.bullGreenSoft : Theme.bearRedSoft

                Text {
                    id: badgeText
                    anchors.centerIn: parent
                    text: root.changeText
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.Bold
                    color: root.isPositive ? Theme.bullGreen : Theme.bearRed
                }
            }

            Text {
                text: root.subText
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                color: Theme.textMuted
                Layout.fillWidth: true
                elide: Text.ElideRight
            }
        }
    }
}
