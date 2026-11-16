import QtQuick
import QtQuick.Controls
import "../theme"

// Tema uyumlu onay kutusu: koyu zeminde siyah kare çizen varsayılan CheckBox yerine kullanılır.
CheckBox {
    id: control

    implicitHeight: 28
    spacing: Theme.spaceSm

    HoverHandler {
        cursorShape: control.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
    }

    indicator: Rectangle {
        implicitWidth: 18
        implicitHeight: 18
        x: control.leftPadding
        y: control.topPadding + (control.availableHeight - height) / 2
        radius: Theme.radiusXs
        color: !control.enabled
               ? Theme.bgSecondary
               : (control.checked ? Theme.accent : (control.hovered ? Theme.bgCardHover : Theme.bgInput))
        border.color: control.checked
                      ? Theme.accent
                      : (control.hovered ? Theme.borderStrong : Theme.borderSubtle)
        border.width: 1

        Behavior on color { ColorAnimation { duration: 120 } }
        Behavior on border.color { ColorAnimation { duration: 120 } }

        ModernIcon {
            anchors.centerIn: parent
            name: "check"
            size: 12
            color: "#FFFFFF"
            visible: control.checked
        }
    }

    contentItem: Text {
        text: control.text
        color: control.enabled ? Theme.textSecondary : Theme.textMuted
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontSm
        verticalAlignment: Text.AlignVCenter
        leftPadding: control.indicator.width + (control.text !== "" ? control.spacing : 0)
    }
}
