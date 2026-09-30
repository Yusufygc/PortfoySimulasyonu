import QtQuick
import QtQuick.Controls
import "../theme"

Rectangle {
    id: root

    property string text: ""
    property string iconName: ""
    property string iconSymbol: ""
    property string variant: "primary" // "primary", "secondary", "ghost", "danger"
    property string tooltip: ""
    signal clicked()

    readonly property color contentColor: {
        if (!root.enabled) return Theme.textMuted
        if (root.variant === "primary" || root.variant === "danger") return "#ffffff"
        return Theme.textPrimary
    }

    implicitWidth: text.length > 0 ? (contentRow.implicitWidth + 20) : implicitHeight
    implicitHeight: 34
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
        spacing: (root.iconName !== "" || root.iconSymbol !== "") && root.text.length > 0 ? 6 : 0

        ModernIcon {
            visible: root.iconName !== ""
            name: root.iconName
            size: 14
            color: root.contentColor
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            visible: root.iconName === "" && root.iconSymbol !== ""
            text: root.iconSymbol
            font.pixelSize: 13
            color: root.contentColor
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            visible: root.text.length > 0
            text: root.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontBase
            font.weight: Font.DemiBold
            color: root.contentColor
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

    ToolTip {
        visible: root.tooltip !== "" && mouseArea.containsMouse
        text: root.tooltip
        delay: 350
        timeout: 4000
    }
}
