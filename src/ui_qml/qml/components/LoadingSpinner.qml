import QtQuick
import "../theme"

// Ortak yükleniyor göstergesi: ince, soluk bir halka üzerinde dönen kısa vurgu yayı.
// BusyIndicator yerine kullanılır; varsayılan boyut küçüktür (size ile ayarlanır).
Item {
    id: root

    property bool running: true
    property real size: 18
    property color color: Theme.accent
    property color trackColor: Theme.borderSubtle
    // Halka kalınlığı boyuta göre ölçeklenir (en az 1.5 px)
    property real thickness: Math.max(1.5, size / 10)

    implicitWidth: size
    implicitHeight: size
    width: size
    height: size
    visible: running
    opacity: running ? 1 : 0

    Behavior on opacity { NumberAnimation { duration: 150 } }

    Canvas {
        id: ring
        anchors.fill: parent
        antialiasing: true

        onPaint: {
            const ctx = getContext("2d")
            ctx.reset()
            const r = (width - root.thickness) / 2
            const cx = width / 2
            const cy = height / 2
            ctx.lineWidth = root.thickness
            ctx.lineCap = "round"

            ctx.strokeStyle = root.trackColor
            ctx.beginPath()
            ctx.arc(cx, cy, r, 0, Math.PI * 2)
            ctx.stroke()

            ctx.strokeStyle = root.color
            ctx.beginPath()
            ctx.arc(cx, cy, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 0.55)
            ctx.stroke()
        }

        Connections {
            target: root
            function onColorChanged() { ring.requestPaint() }
            function onTrackColorChanged() { ring.requestPaint() }
            function onThicknessChanged() { ring.requestPaint() }
        }
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()

        RotationAnimator on rotation {
            running: root.running && root.visible
            from: 0
            to: 360
            duration: 1000
            loops: Animation.Infinite
        }
    }
}
