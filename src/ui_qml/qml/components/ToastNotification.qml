import QtQuick
import QtQuick.Layouts
import "../theme"

Rectangle {
    id: root

    property string message: ""
    property bool isSuccess: true
    property bool isVisible: false

    z: 999
    width: Math.min(420, contentRow.implicitWidth + 32)
    implicitHeight: 46
    radius: Theme.radiusSm

    color: Theme.bgCard
    border.color: isSuccess ? Theme.bullGreen : Theme.bearRed
    border.width: 1

    opacity: isVisible ? 1.0 : 0.0
    y: isVisible ? -20 : 20

    Behavior on opacity { NumberAnimation { duration: 200 } }
    Behavior on y { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }

    RowLayout {
        id: contentRow
        anchors.centerIn: parent
        spacing: 10

        Text {
            text: root.isSuccess ? "✅" : "⚠️"
            font.pixelSize: 16
        }

        Text {
            text: root.message
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontBase
            font.weight: Font.DemiBold
            color: Theme.textPrimary
            elide: Text.ElideRight
        }
    }

    Timer {
        id: dismissTimer
        interval: 3500
        onTriggered: root.isVisible = false
    }

    function show(msg, success = true) {
        root.message = msg
        root.isSuccess = success
        root.isVisible = true
        dismissTimer.restart()
    }
}
