import QtQuick
import QtQuick.Layouts
import "../theme"

ModernCard {
    id: root

    implicitWidth: 340
    implicitHeight: 460

    readonly property var slices: (dashboardController && dashboardController.allocationSlices && dashboardController.allocationSlices.length > 0)
                                  ? dashboardController.allocationSlices
                                  : [
                                      { label: "BIST Hisse Senetleri", pct: 0.68, color: "#2962ff", amount: "₺1.010.221" },
                                      { label: "Eurobond / Fonlar",   pct: 0.19, color: "#089981", amount: "₺282.268" },
                                      { label: "TL Nakit & Mevduat",  pct: 0.13, color: "#ff9800", amount: "₺193.131" },
                                    ]

    onSlicesChanged: {
        donutCanvas.requestPaint()
    }

    Component.onCompleted: {
        donutCanvas.requestPaint()
    }

    Connections {
        target: dashboardController
        function onKpisChanged() {
            donutCanvas.requestPaint()
        }
    }

    ColumnLayout {
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
                    text: (dashboardController && dashboardController.cashRatio)
                          ? ("%" + Math.max(0, 100 - Math.round(parseFloat(dashboardController.cashRatio.replace("%", "")) || 0)))
                          : "%100"
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
                        text: modelData.label
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
                        Layout.preferredWidth: 70
                        horizontalAlignment: Text.AlignRight
                    }
                }
            }
        }

        Item { Layout.fillHeight: true }

        // AI Analiz Kutusu
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 64
            radius: Theme.radiusSm
            color: Theme.bgInput
            border.color: Theme.borderSubtle
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 10

                ModernIcon {
                    name: "target"
                    size: 18
                    color: Theme.bullGreen
                    Layout.alignment: Qt.AlignVCenter
                }

                Column {
                    Layout.fillWidth: true
                    spacing: 2
                    Text {
                        text: Strings.portfolioBalanceStatus
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        font.weight: Font.Bold
                        color: Theme.bullGreen
                    }
                    Text {
                        text: Strings.portfolioBalanceGood
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        color: Theme.textSecondary
                        wrapMode: Text.WordWrap
                        width: 220
                    }
                }
            }
        }
    }
}
