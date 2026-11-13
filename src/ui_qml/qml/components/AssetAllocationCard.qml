import QtQuick
import QtQuick.Layouts
import "../theme"

ModernCard {
    id: root

    implicitWidth: 340
    implicitHeight: contentColumn.implicitHeight + Theme.spaceMd * 2

    // Dilimler: [{ classKey, pct (0-1), color, amount }]; MyPortfolioController.allocationSlices ile beslenir
    property var slices: []

    // Nakit dışındaki dilimlerin toplam payı (donut merkezi)
    readonly property real investedShare: {
        let total = 0
        for (let i = 0; i < slices.length; i++) {
            if (slices[i].classKey !== "CASH") total += slices[i].pct
        }
        return total
    }

    onSlicesChanged: {
        donutCanvas.requestPaint()
    }

    Component.onCompleted: {
        donutCanvas.requestPaint()
    }

    ColumnLayout {
        id: contentColumn
        anchors.fill: parent
        anchors.margins: Theme.spaceMd
        spacing: Theme.spaceMd

        // Başlık
        RowLayout {
            Layout.fillWidth: true
            Text {
                text: Strings.allocationTitle
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontMd
                font.weight: Font.Bold
                color: Theme.textPrimary
                Layout.fillWidth: true
            }
            Text {
                text: root.slices.length + Strings.assetCountSuffix
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                color: Theme.textMuted
            }
        }

        // QML Canvas Donut Chart
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 180

            Canvas {
                id: donutCanvas
                anchors.fill: parent
                antialiasing: true

                onPaint: {
                    const ctx = getContext("2d");
                    ctx.clearRect(0, 0, width, height);

                    const centerX = width / 2;
                    const centerY = height / 2;
                    const radius = Math.min(centerX, centerY) - 10;
                    const innerRadius = radius * 0.68;

                    let startAngle = -Math.PI / 2;

                    for (let i = 0; i < root.slices.length; i++) {
                        const slice = root.slices[i];
                        const sliceAngle = slice.pct * 2 * Math.PI;
                        const endAngle = startAngle + sliceAngle;

                        ctx.beginPath();
                        ctx.arc(centerX, centerY, radius, startAngle, endAngle);
                        ctx.arc(centerX, centerY, innerRadius, endAngle, startAngle, true);
                        ctx.closePath();

                        ctx.fillStyle = slice.color;
                        ctx.fill();

                        // İnce ayraç çizgisi
                        ctx.lineWidth = 2;
                        ctx.strokeStyle = Theme.isDark ? "#242731" : "#ffffff";
                        ctx.stroke();

                        startAngle = endAngle;
                    }
                }
            }

            // Donut Merkezi Metni
            Column {
                anchors.centerIn: parent
                spacing: 2

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: Strings.allocationShare
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    color: Theme.textMuted
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "%" + Math.round(root.investedShare * 100)
                    font.family: Theme.monoFontFamily
                    font.pixelSize: Theme.fontXl
                    font.weight: Font.Bold
                    color: Theme.textPrimary
                }
            }
        }

        // Kategori Göstergeleri (Legend List)
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 8

            Repeater {
                model: root.slices

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Rectangle {
                        width: 10
                        height: 10
                        radius: 3
                        color: modelData.color
                        Layout.alignment: Qt.AlignVCenter
                    }

                    Text {
                        text: Strings.allocationClassName(modelData.classKey)
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        color: Theme.textSecondary
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }

                    Text {
                        text: "%" + Math.round(modelData.pct * 100)
                        font.family: Theme.monoFontFamily
                        font.pixelSize: Theme.fontSm
                        font.weight: Font.Bold
                        color: Theme.textPrimary
                    }

                    Text {
                        text: modelData.amount
                        font.family: Theme.monoFontFamily
                        font.pixelSize: Theme.fontXs
                        color: Theme.textMuted
                        Layout.preferredWidth: 100
                        horizontalAlignment: Text.AlignRight
                    }
                }
            }
        }
    }
}
