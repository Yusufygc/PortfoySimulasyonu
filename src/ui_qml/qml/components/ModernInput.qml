import QtQuick
import QtQuick.Controls
import "../theme"

// Tema uyumlu tek satırlık metin girişi (diyaloglarda ve ayar sekmelerinde ortak kullanılır).
TextField {
    id: root

    property string placeholder: ""

    placeholderText: placeholder
    placeholderTextColor: Theme.textMuted
    color: Theme.textPrimary
    font.family: Theme.fontFamily
    font.pixelSize: Theme.fontBase
    leftPadding: Theme.spaceSm
    rightPadding: Theme.spaceSm
    implicitHeight: 34
    selectByMouse: true

    background: Rectangle {
        color: root.enabled ? Theme.bgInput : Theme.bgSecondary
        radius: Theme.radiusSm
        border.color: root.activeFocus ? Theme.borderFocus : Theme.borderSubtle
        border.width: 1
    }
}
