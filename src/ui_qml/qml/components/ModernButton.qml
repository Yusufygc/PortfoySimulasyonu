import QtQuick
import "../theme"

Rectangle {
    id: root

    property string text: "Buton"
    property string iconSymbol: ""
    property string variant: "primary" // "primary", "secondary", "ghost", "danger"
    signal clicked()

    implicitWidth: Math.max(90, contentRow.implicitWidth + 24)
    implicitHeight: 36
    radius: Theme.radiusSm

    color: {
        if (!enabled) return Theme.bgInput
        if (variant === "primary") {
            return mouseArea.containsMouse ? Theme.accentHover : Theme.accent
        } else if (variant === "danger") {
            return mouseArea.containsMouse ? "#d32f2f" : Theme.bearRed
        } else if (variant === "secondary") {
            return mouseArea.containsMouse ? Theme.bgCardHover : Theme.bgCard
        } else { // ghost
            return mouseArea.containsMouse ? Theme.bgCardHover : "transparent"
        }
    }

    border.color: {
        if (variant === "secondary") return Theme.borderCard
        if (variant === "ghost") return mouseArea.containsMouse ? Theme.borderSubtle : "transparent"
        return "transparent"
    }
    border.width: 1

    scale: mouseArea.pressed ? 0.97 : 1.0

    Behavior on color { ColorAnimation { duration: 120 } }
    Behavior on scale { NumberAnimation { duration: 80 } }

    Row {
        id: contentRow
        anchors.centerIn: parent
        spacing: 6

        Text {
            visible: root.iconSymbol !== ""
            text: root.iconSymbol
            font.pixelSize: 14
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            text: root.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontBase
            font.weight: Font.DemiBold
            color: {
                if (!root.enabled) return Theme.textMuted
                if (root.variant === "primary" || root.variant === "danger") return "#ffffff"
                return Theme.textPrimary
            }
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
