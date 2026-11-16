import QtQuick
import QtQuick.Controls
import "../theme"

// Tema uyumlu aç/kapa anahtarı: koyu zeminde siyah tutamak çizen varsayılan Switch yerine kullanılır.
Switch {
    id: control

    implicitHeight: 26
    spacing: Theme.spaceSm

    HoverHandler {
        cursorShape: control.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
    }

    indicator: Rectangle {
        implicitWidth: 40
        implicitHeight: 22
        x: control.leftPadding
        y: control.topPadding + (control.availableHeight - height) / 2
        radius: 11
        color: !control.enabled
               ? Theme.bgSecondary
               : (control.checked ? Theme.accent : (control.hovered ? Theme.bgCardHover : Theme.bgInput))
        border.color: control.checked
                      ? Theme.accent
                      : (control.hovered ? Theme.borderStrong : Theme.borderSubtle)
        border.width: 1

        Behavior on color { ColorAnimation { duration: 150 } }
        Behavior on border.color { ColorAnimation { duration: 150 } }

        Rectangle {
            x: control.checked ? parent.width - width - 3 : 3
            anchors.verticalCenter: parent.verticalCenter
            width: 16
            height: 16
            radius: 8
            color: control.checked ? "#FFFFFF" : Theme.textSecondary

            Behavior on x { NumberAnimation { duration: 150; easing.type: Easing.InOutQuad } }
            Behavior on color { ColorAnimation { duration: 150 } }
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
