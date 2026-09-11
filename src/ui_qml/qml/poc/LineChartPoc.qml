import QtQuick
import PortfoyCharts 1.0

// d0 POC — QQuickPaintedItem tabanlı LineChartItem'ın gerçek veriyle QML'e bağlanması.
// Renk paleti plan §7.2 "Modern Fintech Dark" tema sabitleridir.
Rectangle {
    id: root
    width: 640
    height: 360
    color: "#0B0F19" // Background

    Rectangle {
        id: card
        anchors.fill: parent
        anchors.margins: 24
        radius: 12
        color: "#151D2C" // Surface (Card)
        border.color: "#26354A"
        border.width: 1

        Text {
            id: title
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.margins: 16
            text: "Kümülatif Getiri (d0 POC)"
            color: "#E5E7EB"
            font.pixelSize: 16
            font.bold: true
        }

        LineChartItem {
            id: chart
            anchors.top: title.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 16
            values: chartValues
            lineColor: "#3B82F6" // Primary Accent
        }
    }
}
