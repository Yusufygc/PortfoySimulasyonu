import QtQuick
import "../theme"

Rectangle {
    id: root

    property bool hoverable: false
    property alias isHovered: mouseArea.containsMouse

    color: hoverable && mouseArea.containsMouse ? Theme.bgCardHover : Theme.bgCard
    border.color: hoverable && mouseArea.containsMouse ? Theme.borderFocus : Theme.borderCard
    border.width: 1
    radius: Theme.radiusMd

    Behavior on color { ColorAnimation { duration: 150 } }
    Behavior on border.color { ColorAnimation { duration: 150 } }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        enabled: root.hoverable
        hoverEnabled: root.hoverable
        cursorShape: root.hoverable ? Qt.PointingHandCursor : Qt.ArrowCursor
    }
}
