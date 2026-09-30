import QtQuick
import "../theme"

Item {
    id: root

    property var points: []
    property bool isUp: true
    property color strokeColor: isUp ? Theme.bullGreen : Theme.bearRed

    implicitWidth: 80
    implicitHeight: 26

    onPointsChanged: canvas.requestPaint()
    onIsUpChanged: canvas.requestPaint()

    Canvas {
        id: canvas
        anchors.fill: parent
        antialiasing: true

        onPaint: {
            const ctx = getContext("2d");
            ctx.clearRect(0, 0, width, height);

            const pts = root.points;
            if (!pts || pts.length < 2) {
                // Nötr düz çizgi
                ctx.beginPath();
                ctx.moveTo(2, height / 2);
                ctx.lineTo(width - 2, height / 2);
                ctx.strokeStyle = Theme.borderCard;
                ctx.lineWidth = 1.5;
                ctx.stroke();
                return;
            }

            let minVal = pts[0];
            let maxVal = pts[0];
            for (let i = 1; i < pts.length; i++) {
                if (pts[i] < minVal) minVal = pts[i];
                if (pts[i] > maxVal) maxVal = pts[i];
            }

            const range = Math.max(0.0001, maxVal - minVal);
            const padX = 2;
            const padY = 4;
            const usableW = width - (padX * 2);
            const usableH = height - (padY * 2);
            const stepX = usableW / (pts.length - 1);

            const coords = [];
            for (let i = 0; i < pts.length; i++) {
                const x = padX + (i * stepX);
                const normY = (pts[i] - minVal) / range;
                const y = height - padY - (normY * usableH);
                coords.push({ x: x, y: y });
            }

            // Gradyan alan doldurma
            ctx.beginPath();
            ctx.moveTo(coords[0].x, height);
            ctx.lineTo(coords[0].x, coords[0].y);
            for (let i = 1; i < coords.length; i++) {
                ctx.lineTo(coords[i].x, coords[i].y);
            }
            ctx.lineTo(coords[coords.length - 1].x, height);
            ctx.closePath();

            const grad = ctx.createLinearGradient(0, 0, 0, height);
            if (root.isUp) {
                grad.addColorStop(0, "rgba(8, 153, 129, 0.28)");
                grad.addColorStop(1, "rgba(8, 153, 129, 0.0)");
            } else {
                grad.addColorStop(0, "rgba(242, 54, 69, 0.28)");
                grad.addColorStop(1, "rgba(242, 54, 69, 0.0)");
            }
            ctx.fillStyle = grad;
            ctx.fill();

            // Çizgi çizimi
            ctx.beginPath();
            ctx.moveTo(coords[0].x, coords[0].y);
            for (let i = 1; i < coords.length; i++) {
                ctx.lineTo(coords[i].x, coords[i].y);
            }
            ctx.strokeStyle = root.strokeColor;
            ctx.lineWidth = 1.8;
            ctx.lineCap = "round";
            ctx.lineJoin = "round";
            ctx.stroke();

            // Son noktayı vurgula
            const last = coords[coords.length - 1];
            ctx.beginPath();
            ctx.arc(last.x, last.y, 2.2, 0, 2 * Math.PI);
            ctx.fillStyle = root.strokeColor;
            ctx.fill();
        }
    }
}
