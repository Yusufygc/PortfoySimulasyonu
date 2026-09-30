import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

ModernCard {
    id: root

    implicitWidth: 640
    implicitHeight: 380
    Layout.fillWidth: true
    Layout.minimumHeight: 340
    Layout.preferredHeight: 380

    readonly property var bars: (typeof stock360Controller !== "undefined" && stock360Controller && stock360Controller.financialBars)
                                ? stock360Controller.financialBars
                                : []

    readonly property string currentTab: (typeof stock360Controller !== "undefined" && stock360Controller && stock360Controller.activeFinancialTab)
                                        ? stock360Controller.activeFinancialTab
                                        : "satis"

    property int hoveredBarIndex: -1

    onBarsChanged: {
        chartCanvas.requestPaint()
    }

    Connections {
        target: (typeof stock360Controller !== "undefined") ? stock360Controller : null
        function onFinancialsChanged() {
            chartCanvas.requestPaint()
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spaceMd
        spacing: Theme.spaceSm

        // Header: Title & Metric Tabs
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            ColumnLayout {
                spacing: 2
                Layout.fillWidth: true

                RowLayout {
                    spacing: 6
                    Rectangle {
                        width: 18
                        height: 18
                        radius: Theme.radiusSm
                        color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.15)
                        Layout.alignment: Qt.AlignVCenter

                        ModernIcon {
                            anchors.centerIn: parent
                            name: "barchart"
                            size: 11
                            color: Theme.accent
                        }
                    }

                    Text {
                        text: Strings.financialsTitle
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        font.weight: Font.Bold
                        color: Theme.textPrimary
                        font.letterSpacing: 0.5
                    }
                }

                Text {
                    text: stock360Controller ? stock360Controller.financialSummary : ""
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    color: Theme.textMuted
                    visible: text !== ""
                }
            }

            // Tab Buttons (Net Satışlar / Brüt Kâr / FAVÖK / Net Kâr)
            Row {
                spacing: 4
                Layout.alignment: Qt.AlignRight | Qt.AlignVCenter

                Repeater {
                    model: [
                        { key: "satis", label: Strings.tabRevenue },
                        { key: "brut_kar", label: Strings.tabGrossProfit },
                        { key: "favok", label: Strings.tabEbitda },
                        { key: "net_kar", label: Strings.tabNetIncome },
                    ]

                    Rectangle {
                        id: tabBtn
                        property bool isSelected: root.currentTab === modelData.key
                        implicitWidth: tabLabel.implicitWidth + 16
                        implicitHeight: 28
                        radius: Theme.radiusSm
                        color: isSelected
                               ? Theme.accent
                               : (tabMouse.containsMouse ? Theme.bgCardHover : Theme.bgInput)
                        border.color: isSelected ? Theme.accent : Theme.borderSubtle
                        border.width: 1

                        Behavior on color { ColorAnimation { duration: 120 } }

                        Text {
                            id: tabLabel
                            anchors.centerIn: parent
                            text: modelData.label
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            font.weight: tabBtn.isSelected ? Font.Bold : Font.Normal
                            color: tabBtn.isSelected ? "#ffffff" : Theme.textSecondary
                        }

                        MouseArea {
                            id: tabMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (stock360Controller) {
                                    stock360Controller.setFinancialTab(modelData.key)
                                }
                            }
                        }
                    }
                }
            }
        }

        // Separator
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: Theme.borderSubtle
        }

        // QML Canvas Bar Chart Area
        Item {
            id: canvasContainer
            Layout.fillWidth: true
            Layout.fillHeight: true

            Canvas {
                id: chartCanvas
                anchors.fill: parent
                antialiasing: true

                onPaint: {
                    const ctx = getContext("2d");
                    ctx.clearRect(0, 0, width, height);

                    const data = root.bars;
                    if (!data || data.length === 0) {
                        ctx.fillStyle = Theme.textMuted;
                        ctx.font = "12px sans-serif";
                        ctx.textAlign = "center";
                        ctx.fillText("Finansal grafik verisi bulunamadı", width / 2, height / 2);
                        return;
                    }

                    const paddingLeft = 40;
                    const paddingRight = 30;
                    const paddingTop = 36;
                    const paddingBottom = 32;

                    const plotWidth = width - paddingLeft - paddingRight;
                    const plotHeight = height - paddingTop - paddingBottom;
                    const baselineY = height - paddingBottom;

                    // Subtle horizontal grid lines
                    ctx.lineWidth = 1;
                    ctx.strokeStyle = Theme.isDark ? "#2a2e39" : "#e6e8ea";
                    const gridSteps = 3;
                    for (let g = 0; g <= gridSteps; g++) {
                        const y = paddingTop + (plotHeight / gridSteps) * g;
                        ctx.beginPath();
                        ctx.moveTo(paddingLeft, y);
                        ctx.lineTo(width - paddingRight, y);
                        ctx.stroke();
                    }

                    const n = data.length;
                    const slotWidth = plotWidth / n;
                    const barWidth = Math.min(64, Math.max(28, slotWidth * 0.55));

                    for (let i = 0; i < n; i++) {
                        const bar = data[i];
                        const xCenter = paddingLeft + slotWidth * i + slotWidth / 2;
                        const x = xCenter - barWidth / 2;

                        const barHeight = Math.max(4, plotHeight * bar.ratio * 0.88);
                        const y = baselineY - barHeight;

                        const isHovered = (root.hoveredBarIndex === i);

                        // Gradient fill
                        const grad = ctx.createLinearGradient(x, y, x, baselineY);
                        if (bar.isPositive) {
                            if (isHovered) {
                                grad.addColorStop(0, "#407bff");
                                grad.addColorStop(1, Qt.rgba(0.16, 0.38, 1.0, 0.4));
                            } else {
                                grad.addColorStop(0, Theme.accent);
                                grad.addColorStop(1, Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.25));
                            }
                        } else {
                            if (isHovered) {
                                grad.addColorStop(0, "#ff5252");
                                grad.addColorStop(1, Qt.rgba(0.96, 0.26, 0.21, 0.4));
                            } else {
                                grad.addColorStop(0, Theme.bearRed);
                                grad.addColorStop(1, Qt.rgba(Theme.bearRed.r, Theme.bearRed.g, Theme.bearRed.b, 0.25));
                            }
                        }

                        // Draw Rounded Bar
                        ctx.fillStyle = grad;
                        ctx.beginPath();
                        const r = Math.min(6, barWidth / 2);
                        ctx.moveTo(x, baselineY);
                        ctx.lineTo(x, y + r);
                        ctx.quadraticCurveTo(x, y, x + r, y);
                        ctx.lineTo(x + barWidth - r, y);
                        ctx.quadraticCurveTo(x + barWidth, y, x + barWidth, y + r);
                        ctx.lineTo(x + barWidth, baselineY);
                        ctx.closePath();
                        ctx.fill();

                        // Border outline for active bar
                        if (isHovered) {
                            ctx.lineWidth = 1.5;
                            ctx.strokeStyle = "#ffffff";
                            ctx.stroke();
                        }

                        // Amount text on top of bar
                        ctx.font = isHovered ? "bold 11px sans-serif" : "10px sans-serif";
                        ctx.fillStyle = isHovered ? Theme.textPrimary : Theme.textSecondary;
                        ctx.textAlign = "center";
                        ctx.fillText(bar.amount, xCenter, y - 8);

                        // Quarter period label on X axis
                        ctx.font = isHovered ? "bold 11px sans-serif" : "10px sans-serif";
                        ctx.fillStyle = isHovered ? Theme.textPrimary : Theme.textMuted;
                        ctx.fillText(bar.period, xCenter, baselineY + 18);
                    }

                    // Baseline
                    ctx.lineWidth = 1;
                    ctx.strokeStyle = Theme.isDark ? "#363a45" : "#d1d4dc";
                    ctx.beginPath();
                    ctx.moveTo(paddingLeft - 10, baselineY);
                    ctx.lineTo(width - paddingRight + 10, baselineY);
                    ctx.stroke();
                }
            }

            // Mouse interaction for hover effect
            MouseArea {
                anchors.fill: parent
                hoverEnabled: true
                onPositionChanged: function(mouse) {
                    const data = root.bars;
                    if (!data || data.length === 0) return;

                    const paddingLeft = 40;
                    const paddingRight = 30;
                    const plotWidth = width - paddingLeft - paddingRight;
                    const n = data.length;
                    const slotWidth = plotWidth / n;

                    if (mouse.x < paddingLeft || mouse.x > width - paddingRight) {
                        if (root.hoveredBarIndex !== -1) {
                            root.hoveredBarIndex = -1;
                            chartCanvas.requestPaint();
                        }
                        return;
                    }

                    const index = Math.floor((mouse.x - paddingLeft) / slotWidth);
                    if (index >= 0 && index < n && index !== root.hoveredBarIndex) {
                        root.hoveredBarIndex = index;
                        chartCanvas.requestPaint();
                    }
                }

                onExited: {
                    if (root.hoveredBarIndex !== -1) {
                        root.hoveredBarIndex = -1;
                        chartCanvas.requestPaint();
                    }
                }
            }
        }
    }
}
