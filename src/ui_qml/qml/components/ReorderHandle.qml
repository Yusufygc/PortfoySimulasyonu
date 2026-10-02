import QtQuick
import "../theme"

// Liste satırı için sürükle-bırak sıralama tutamağı.
// Kullanım: delegate içine koyun; delegate'in `dragOffset` özelliği ve `transform: Translate { y: dragOffset }` olmalı.
// Bırakıldığında kaç satır kaydığı hesaplanır ve moveRequested(kaynakIndeks, hedefIndeks) yayılır.
Item {
    id: root

    property Item target: null     // sürüklenen satır (delegate)
    property int rowIndex: 0
    property int rowCount: 0
    property real step: 48         // satır yüksekliği + aralık

    signal moveRequested(int fromIndex, int toIndex)

    implicitWidth: 18
    implicitHeight: 28

    function targetIndex(deltaY) {
        const shift = Math.round(deltaY / Math.max(1, step))
        return Math.max(0, Math.min(rowCount - 1, rowIndex + shift))
    }

    Grid {
        anchors.centerIn: parent
        columns: 2
        rowSpacing: 3
        columnSpacing: 3
        Repeater {
            model: 6
            Rectangle {
                width: 3
                height: 3
                radius: 1.5
                color: grip.pressed || grip.containsMouse ? Theme.accent : Theme.textMuted
            }
        }
    }

    MouseArea {
        id: grip
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
        preventStealing: true

        property real pressSceneY: 0

        function sceneY(mouse) {
            return mapToItem(null, mouse.x, mouse.y).y
        }

        onPressed: function(mouse) {
            pressSceneY = sceneY(mouse)
            if (root.target) root.target.z = 100
        }
        onPositionChanged: function(mouse) {
            if (!pressed || !root.target) return
            const delta = sceneY(mouse) - pressSceneY
            // Liste sınırları dışına taşmayı engelle
            const minDelta = -root.rowIndex * root.step
            const maxDelta = (root.rowCount - 1 - root.rowIndex) * root.step
            root.target.dragOffset = Math.max(minDelta, Math.min(maxDelta, delta))
        }
        onReleased: function(mouse) {
            const delta = sceneY(mouse) - pressSceneY
            const to = root.targetIndex(delta)
            if (root.target) {
                root.target.dragOffset = 0
                root.target.z = 0
            }
            if (to !== root.rowIndex) root.moveRequested(root.rowIndex, to)
        }
        onCanceled: {
            if (root.target) {
                root.target.dragOffset = 0
                root.target.z = 0
            }
        }
    }
}
