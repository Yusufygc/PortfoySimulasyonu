import QtQuick
import QtQuick.Layouts
import "../theme"

// Grafik açıklama kartı: "Nedir" ve "Nasıl Yorumlanır". Başlığa tıklayınca açılır/kapanır.
Rectangle {
    id: root

    property string title: ""
    property string what: ""
    property string how: ""
    property bool expanded: false

    Layout.fillWidth: true
    implicitHeight: infoColumn.implicitHeight + Theme.spaceSm * 2
    radius: Theme.radiusSm
    color: Theme.bgSecondary
    border.color: Theme.borderSubtle
    border.width: 1

    ColumnLayout {
        id: infoColumn
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: Theme.spaceSm
        spacing: Theme.spaceXs

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceXs

            ModernIcon {
                name: "info"
                color: Theme.accent
                size: 14
            }

            Text {
                text: root.title
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                font.weight: Font.DemiBold
                elide: Text.ElideRight
                Layout.fillWidth: true
            }

            Text {
                text: root.expanded ? "−" : "+"
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBase
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: root.expanded = !root.expanded
            }
        }

        Text {
            visible: root.expanded
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            textFormat: Text.StyledText
            text: "<b>" + Strings.compareInfoWhat + ":</b> " + root.what
            color: Theme.textSecondary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontXs
        }

        Text {
            visible: root.expanded
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            textFormat: Text.StyledText
            text: "<b>" + Strings.compareInfoHow + ":</b> " + root.how
            color: Theme.textSecondary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontXs
        }
    }
}
