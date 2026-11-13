import QtQuick
import QtQuick.Controls
import "../theme"

// Tema renkli kaydırıcı: varsayılan stil koyu zeminde siyah tutamak çiziyordu (2026-11-08 QA).
Slider {
    id: control

    background: Rectangle {
        x: control.leftPadding
        y: control.topPadding + control.availableHeight / 2 - height / 2
        width: control.availableWidth
        height: 4
        radius: 2
        color: Theme.borderSubtle

        Rectangle {
            width: control.visualPosition * parent.width
            height: parent.height
            radius: 2
            color: Theme.accent
        }
    }

    handle: Rectangle {
        x: control.leftPadding + control.visualPosition * (control.availableWidth - width)
        y: control.topPadding + control.availableHeight / 2 - height / 2
        width: 16
        height: 16
        radius: 8
        color: control.pressed ? Theme.accentHover : Theme.accent
        border.color: Theme.bgPrimary
        border.width: 2
    }
}
