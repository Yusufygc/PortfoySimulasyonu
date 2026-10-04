import QtQuick
import QtQuick.Controls
import "../theme"

// Fiyat durumu: son güncelleme zamanı ve küçük yenile ikonu (PriceRefreshController).
// Fiyatlar kendiliğinden güncellenir; ikon yalnızca elle tetikleme içindir (seans içinde canlı, dışında kapanış verisi).
Row {
    id: root

    readonly property bool hasController: typeof priceRefreshController !== "undefined" && priceRefreshController !== null
    readonly property bool busy: hasController && priceRefreshController.isRefreshing

    spacing: Theme.spaceXs

    Text {
        anchors.verticalCenter: parent.verticalCenter
        text: root.busy ? Strings.priceStatusRefreshing
              : (root.hasController && priceRefreshController.lastUpdateText !== "" ? priceRefreshController.lastUpdateText : Strings.priceStatusNever)
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontXs
        color: Theme.textMuted
    }

    Rectangle {
        id: refreshButton
        anchors.verticalCenter: parent.verticalCenter
        width: 22
        height: 22
        radius: Theme.radiusSm
        color: refreshArea.containsMouse && !root.busy ? Theme.bgSurfaceHover : "transparent"

        ModernIcon {
            id: refreshIcon
            anchors.centerIn: parent
            name: "refresh"
            size: 13
            color: root.busy ? Theme.accent : Theme.textMuted

            RotationAnimator on rotation {
                running: root.busy
                from: 0
                to: 360
                duration: 900
                loops: Animation.Infinite
                onRunningChanged: if (!running) refreshIcon.rotation = 0
            }
        }

        MouseArea {
            id: refreshArea
            anchors.fill: parent
            hoverEnabled: true
            enabled: root.hasController && !root.busy
            cursorShape: Qt.PointingHandCursor
            onClicked: priceRefreshController.refreshNow()
        }

        ToolTip.visible: refreshArea.containsMouse
        ToolTip.delay: 500
        ToolTip.text: Strings.priceStatusRefreshTooltip
    }
}
