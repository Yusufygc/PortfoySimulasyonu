import QtQuick
import QtQuick.Layouts
import "../theme"

Rectangle {
    id: root

    property string message: ""
    property bool isSuccess: true
    property bool isVisible: false

    // Genişlik en çok 420; uzun metin satıra sarılır ve kutu yüksekliği metne uyar (eskiden metin kutudan taşıyordu)
    readonly property int maxWidth: 420
    readonly property int sidePadding: 16
    readonly property int iconSize: 16
    readonly property int gap: 10

    z: 999
    width: Math.min(maxWidth, sidePadding * 2 + iconSize + gap + Math.ceil(measure.advanceWidth) + 2)
    implicitHeight: Math.max(46, toastText.contentHeight + 24)
    radius: Theme.radiusSm

    color: Theme.bgCard
    border.color: isSuccess ? Theme.bullGreen : Theme.bearRed
    border.width: 1

    opacity: isVisible ? 1.0 : 0.0
    y: isVisible ? -20 : 20

    Behavior on opacity { NumberAnimation { duration: 200 } }
    Behavior on y { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }

    // Metnin tek satırdaki doğal genişliği (sarmadan önce)
    TextMetrics {
        id: measure
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontBase
        font.weight: Font.DemiBold
        text: root.message
    }

    RowLayout {
        id: contentRow
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: root.sidePadding
        anchors.rightMargin: root.sidePadding
        spacing: root.gap

        ModernIcon {
            name: root.isSuccess ? "check" : "alert"
            size: root.iconSize
            color: root.isSuccess ? Theme.bullGreen : Theme.bearRed
            Layout.alignment: Qt.AlignVCenter
        }

        Text {
            id: toastText
            objectName: "toastText"
            Layout.fillWidth: true
            text: root.message
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontBase
            font.weight: Font.DemiBold
            color: Theme.textPrimary
            wrapMode: Text.Wrap
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
