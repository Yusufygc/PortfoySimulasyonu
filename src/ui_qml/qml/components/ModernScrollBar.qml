import QtQuick
import QtQuick.Controls
import "../theme"

ScrollBar {
    id: control

    implicitWidth: orientation === Qt.Vertical ? (hovered || pressed ? 10 : 6) : 100
    implicitHeight: orientation === Qt.Horizontal ? (hovered || pressed ? 10 : 6) : 100
    policy: ScrollBar.AsNeeded
    hoverEnabled: true

    contentItem: Rectangle {
        implicitWidth: control.orientation === Qt.Vertical ? (control.hovered || control.pressed ? 10 : 6) : 24
        implicitHeight: control.orientation === Qt.Horizontal ? (control.hovered || control.pressed ? 10 : 6) : 24
        radius: control.orientation === Qt.Vertical ? width / 2 : height / 2

        color: {
            if (control.pressed) return Theme.scrollbarThumbActive
            if (control.hovered) return Theme.scrollbarThumbHover
            return Theme.scrollbarThumb
        }

        // Aktif kaydırmada veya hover/pressed durumunda tam belirgin (0.90),
        // Boştayken içeriğin taştığını belli edecek kadar zarif ve yarı saydam (0.35)
        opacity: (control.active || control.hovered || control.pressed) ? 0.90 : (control.size < 1.0 ? 0.35 : 0.0)

        Behavior on implicitWidth {
            NumberAnimation { duration: 140; easing.type: Easing.OutCubic }
        }
        Behavior on implicitHeight {
            NumberAnimation { duration: 140; easing.type: Easing.OutCubic }
        }
        Behavior on opacity {
            NumberAnimation { duration: 250; easing.type: Easing.OutCubic }
        }
        Behavior on color {
            ColorAnimation { duration: 150 }
        }
    }

    background: Rectangle {
        color: "transparent"
    }
}
