import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

ModernCard {
    id: root

    readonly property var ctrl: (typeof stock360Controller !== "undefined") ? stock360Controller : null

    implicitHeight: 390
    Layout.fillWidth: true

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spaceMd
        spacing: Theme.spaceSm

        // Üst Başlık & Gösterge İpuçları (Legend)
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            RowLayout {
                spacing: 6
                Layout.fillWidth: true

                Rectangle {
                    width: 20
                    height: 20
                    radius: Theme.radiusSm
                    color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.15)
                    Layout.alignment: Qt.AlignVCenter

                    ModernIcon {
                        anchors.centerIn: parent
                        name: "bar-chart-2"
                        size: 12
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

            // Göstergeler (Legend)
            RowLayout {
                spacing: 12
                Layout.alignment: Qt.AlignVCenter

                // Net Satışlar (Mavi)
                RowLayout {
                    spacing: 5
                    Rectangle {
                        width: 10
                        height: 10
                        radius: 2
                        color: Theme.accent
                    }
                    Text {
                        text: Strings.tabRevenue
                        font.family: Theme.fontFamily
                        font.pixelSize: 11
                        color: Theme.textMuted
                    }
                }

                // Net Kâr (Zümrüt Yeşili)
                RowLayout {
                    spacing: 5
                    Rectangle {
                        width: 10
                        height: 10
                        radius: 2
                        color: Theme.bullGreen
                    }
                    Text {
                        text: Strings.tabNetIncome
                        font.family: Theme.fontFamily
                        font.pixelSize: 11
                        color: Theme.textMuted
                    }
                }

                // Net Kâr Marjı (Turuncu Çizgi)
                RowLayout {
                    spacing: 5
                    Rectangle {
                        width: 12
                        height: 3
                        radius: 1.5
                        color: "#f59e0b"
                    }
                    Text {
                        text: "% " + Strings.labelNetMargin
                        font.family: Theme.fontFamily
                        font.pixelSize: 11
                        color: Theme.textMuted
                    }
                }
            }
        }

        // Ayırıcı İnce Çizgi
        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.borderSubtle
        }

        // Ana Çizim Alanı (Canvas + Hover Tooltip)
        Item {
            id: chartArea
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            property var chartData: (root.ctrl && root.ctrl.revenueChartData) ? root.ctrl.revenueChartData : []
            property int hoverIndex: -1
            property real hoverX: 0
            property real hoverY: 0

            onChartDataChanged: canvas.requestPaint()

            Connections {
                target: Theme
                function onIsDarkChanged() { canvas.requestPaint() }
            }

            Canvas {
                id: canvas
                anchors.fill: parent
                renderTarget: Canvas.FramebufferObject
                renderStrategy: Canvas.Threaded

                onPaint: {
                    var ctx = getContext("2d");
                    ctx.reset();

                    var w = width;
                    var h = height;
                    var data = chartArea.chartData;
                    if (!data || data.length === 0) {
                        ctx.fillStyle = Theme.isDark ? "#64748b" : "#94a3b8";
                        ctx.font = "12px sans-serif";
                        ctx.textAlign = "center";
                        ctx.textBaseline = "middle";
                        ctx.fillText(Strings.financialChartLoading, w / 2, h / 2);
                        return;
                    }

                    var paddingLeft = 16;
                    var paddingRight = 16;
                    var paddingTop = 20;
                    var paddingBottom = 32;
                    var drawW = w - paddingLeft - paddingRight;
                    var drawH = h - paddingTop - paddingBottom;

                    // Maksimum ve minimum değerleri bul
                    var maxRev = 0;
                    var maxMargin = 0;
                    var minMargin = 0;

                    for (var i = 0; i < data.length; i++) {
                        var rev = data[i].revenue || 0;
                        var ni = data[i].net_income || 0;
                        if (rev > maxRev) maxRev = rev;
                        if (ni > maxRev) maxRev = ni;

                        var mg = data[i].margin || 0;
                        if (mg > maxMargin) maxMargin = mg;
                        if (mg < minMargin) minMargin = mg;
                    }
                    if (maxRev <= 0) maxRev = 1;
                    if (maxMargin <= 0) maxMargin = 10;
                    // %15 tavan payı
                    maxRev = maxRev * 1.15;
                    maxMargin = maxMargin * 1.25;

                    // Arka plan yatay ızgara çizgileri (Grid Lines)
                    var gridSteps = 4;
                    ctx.strokeStyle = Theme.isDark ? "rgba(255, 255, 255, 0.05)" : "rgba(0, 0, 0, 0.05)";
                    ctx.lineWidth = 1;
                    ctx.setLineDash([4, 4]);

                    for (var g = 0; g <= gridSteps; g++) {
                        var gy = paddingTop + (drawH / gridSteps) * g;
                        ctx.beginPath();
                        ctx.moveTo(paddingLeft, gy);
                        ctx.lineTo(w - paddingRight, gy);
                        ctx.stroke();
                    }
                    ctx.setLineDash([]);

                    // Sütunların genişliği ve aralıkları
                    var n = data.length;
                    var slotWidth = drawW / n;
                    var barWidth = Math.min(22, Math.max(8, (slotWidth - 12) / 2));

                    var marginPoints = [];

                    // 1. Sütunları Çiz (Net Satışlar & Net Kâr)
                    for (var k = 0; k < n; k++) {
                        var item = data[k];
                        var slotCenterX = paddingLeft + k * slotWidth + slotWidth / 2;

                        var revH = Math.max(2, (item.revenue / maxRev) * drawH);
                        var revX = slotCenterX - barWidth - 1;
                        var revY = paddingTop + drawH - revH;

                        // Satış Sütunu (Accent)
                        ctx.fillStyle = Theme.accent;
                        drawRoundedRect(ctx, revX, revY, barWidth, revH, 3);

                        // Net Kâr Sütunu
                        var niH = Math.max(2, (Math.abs(item.net_income) / maxRev) * drawH);
                        var niX = slotCenterX + 1;
                        var niY = paddingTop + drawH - niH;

                        ctx.fillStyle = (item.net_income >= 0) ? Theme.bullGreen : Theme.bearRed;
                        drawRoundedRect(ctx, niX, niY, barWidth, niH, 3);

                        // Dönem Etiketi (X Ekseni)
                        ctx.fillStyle = Theme.isDark ? "#94a3b8" : "#64748b";
                        ctx.font = "10px sans-serif";
                        ctx.textAlign = "center";
                        ctx.textBaseline = "top";
                        ctx.fillText(item.period || "", slotCenterX, paddingTop + drawH + 8);

                        // Marj Çizgisi Noktası
                        var marginNorm = (item.margin - minMargin) / (maxMargin - minMargin);
                        var marginY = paddingTop + drawH - (marginNorm * drawH);
                        marginPoints.push({ x: slotCenterX, y: marginY, margin: item.margin, marginStr: item.margin_str });
                    }

                    // 2. Net Kâr Marjı Eğrisini Çiz (Spline / Line)
                    if (marginPoints.length > 1) {
                        ctx.strokeStyle = "#f59e0b";
                        ctx.lineWidth = 2.5;
                        ctx.beginPath();
                        ctx.moveTo(marginPoints[0].x, marginPoints[0].y);

                        for (var p = 1; p < marginPoints.length; p++) {
                            var prev = marginPoints[p - 1];
                            var cur = marginPoints[p];
                            var cpX = (prev.x + cur.x) / 2;
                            ctx.bezierCurveTo(cpX, prev.y, cpX, cur.y, cur.x, cur.y);
                        }
                        ctx.stroke();

                        // Marj Noktaları (Dots)
                        for (var d = 0; d < marginPoints.length; d++) {
                            var pt = marginPoints[d];
                            ctx.fillStyle = "#f59e0b";
                            ctx.beginPath();
                            ctx.arc(pt.x, pt.y, 4, 0, Math.PI * 2);
                            ctx.fill();
                            ctx.strokeStyle = Theme.bgCard;
                            ctx.lineWidth = 2;
                            ctx.stroke();
                        }
                    }

                    // 3. Hover Kılavuz Çizgisi
                    if (chartArea.hoverIndex >= 0 && chartArea.hoverIndex < n) {
                        var hX = paddingLeft + chartArea.hoverIndex * slotWidth + slotWidth / 2;
                        ctx.strokeStyle = Theme.isDark ? "rgba(255, 255, 255, 0.3)" : "rgba(0, 0, 0, 0.25)";
                        ctx.lineWidth = 1;
                        ctx.setLineDash([2, 2]);
                        ctx.beginPath();
                        ctx.moveTo(hX, paddingTop);
                        ctx.lineTo(hX, paddingTop + drawH);
                        ctx.stroke();
                        ctx.setLineDash([]);
                    }
                }

                function drawRoundedRect(ctx, x, y, width, height, radius) {
                    if (height < radius * 2) radius = height / 2;
                    ctx.beginPath();
                    ctx.moveTo(x + radius, y);
                    ctx.lineTo(x + width - radius, y);
                    ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
                    ctx.lineTo(x + width, y + height);
                    ctx.lineTo(x, y + height);
                    ctx.lineTo(x, y + radius);
                    ctx.quadraticCurveTo(x, y, x + radius, y);
                    ctx.closePath();
                    ctx.fill();
                }
            }

            // Fare ile Etkileşim (Hover & Tooltip)
            MouseArea {
                anchors.fill: parent
                hoverEnabled: true

                onPositionChanged: function(mouse) {
                    var data = chartArea.chartData;
                    if (!data || data.length === 0) return;

                    var paddingLeft = 16;
                    var paddingRight = 16;
                    var drawW = chartArea.width - paddingLeft - paddingRight;
                    var slotWidth = drawW / data.length;

                    var relX = mouse.x - paddingLeft;
                    if (relX >= 0 && relX <= drawW) {
                        var idx = Math.floor(relX / slotWidth);
                        if (idx >= 0 && idx < data.length) {
                            chartArea.hoverIndex = idx;
                            chartArea.hoverX = mouse.x;
                            chartArea.hoverY = mouse.y;
                            canvas.requestPaint();
                            return;
                        }
                    }
                    if (chartArea.hoverIndex !== -1) {
                        chartArea.hoverIndex = -1;
                        canvas.requestPaint();
                    }
                }

                onExited: {
                    chartArea.hoverIndex = -1;
                    canvas.requestPaint();
                }
            }

            // Hover Tooltip Kartı
            Rectangle {
                id: tooltip
                visible: chartArea.hoverIndex >= 0 && chartArea.hoverIndex < chartArea.chartData.length
                z: 10
                width: 170
                height: 95
                radius: Theme.radiusSm
                color: Theme.isDark ? "#1e293b" : "#ffffff"
                border.color: Theme.borderSubtle
                border.width: 1

                // Akıllı konumlandırma: sağa taşarsa sola kay
                x: Math.min(chartArea.width - width - 8, Math.max(8, chartArea.hoverX + 12))
                y: Math.max(10, Math.min(chartArea.height - height - 10, chartArea.hoverY - 40))

                property var activeItem: (chartArea.hoverIndex >= 0 && chartArea.hoverIndex < chartArea.chartData.length)
                                         ? chartArea.chartData[chartArea.hoverIndex] : null

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 4

                    Text {
                        text: tooltip.activeItem ? tooltip.activeItem.period : ""
                        font.family: Theme.fontFamily
                        font.pixelSize: 11
                        font.weight: Font.Bold
                        color: Theme.textPrimary
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.borderSubtle
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: Strings.tabRevenue + ":"
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                            color: Theme.textMuted
                        }
                        Item { Layout.fillWidth: true }
                        Text {
                            text: (tooltip.activeItem && (tooltip.activeItem.revenueStr || tooltip.activeItem.revenue_str))
                                  ? ("" + (tooltip.activeItem.revenueStr || tooltip.activeItem.revenue_str))
                                  : "—"
                            font.family: Theme.fontMono
                            font.pixelSize: 10
                            font.weight: Font.DemiBold
                            color: Theme.accent
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: Strings.tabNetIncome + ":"
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                            color: Theme.textMuted
                        }
                        Item { Layout.fillWidth: true }
                        Text {
                            text: (tooltip.activeItem && (tooltip.activeItem.netIncomeStr || tooltip.activeItem.net_income_str))
                                  ? ("" + (tooltip.activeItem.netIncomeStr || tooltip.activeItem.net_income_str))
                                  : "—"
                            font.family: Theme.fontMono
                            font.pixelSize: 10
                            font.weight: Font.DemiBold
                            color: Theme.bullGreen
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: Strings.labelNetMargin + ":"
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                            color: Theme.textMuted
                        }
                        Item { Layout.fillWidth: true }
                        Text {
                            text: (tooltip.activeItem && (tooltip.activeItem.marginStr || tooltip.activeItem.margin_str))
                                  ? ("" + (tooltip.activeItem.marginStr || tooltip.activeItem.margin_str))
                                  : "—"
                            font.family: Theme.fontMono
                            font.pixelSize: 10
                            font.weight: Font.Bold
                            color: "#f59e0b"
                        }
                    }
                }
            }
        }

        // Alt KPI Kartları (4'lü Finansal Özet Rozetleri)
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            // 1. Son Çeyrek Satış
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 46
                radius: Theme.radiusSm
                color: Theme.bgInput
                border.color: Theme.borderSubtle
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 8

                    ModernIcon {
                        name: "bar-chart-2"
                        size: 14
                        color: Theme.accent
                    }

                    ColumnLayout {
                        spacing: 1
                        Text {
                            text: Strings.revLastQuarterSales
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                            color: Theme.textMuted
                        }
                        Text {
                            text: root.ctrl ? root.ctrl.latestQuarterRevenue : "—"
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.Bold
                            color: Theme.textPrimary
                        }
                    }
                }
            }

            // 2. Satış Büyümesi (YoY)
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 46
                radius: Theme.radiusSm
                color: Theme.bgInput
                border.color: Theme.borderSubtle
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 8

                    ModernIcon {
                        name: (root.ctrl && root.ctrl.isRevenueYoYPositive) ? "trendingup" : "trendingdown"
                        size: 14
                        color: (root.ctrl && root.ctrl.isRevenueYoYPositive) ? Theme.bullGreen : Theme.bearRed
                    }

                    ColumnLayout {
                        spacing: 1
                        Text {
                            text: Strings.revSalesGrowthYoY
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                            color: Theme.textMuted
                        }
                        Text {
                            text: root.ctrl ? root.ctrl.revenueYoYGrowth : "—"
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.Bold
                            color: (root.ctrl && root.ctrl.isRevenueYoYPositive) ? Theme.bullGreen : Theme.bearRed
                        }
                    }
                }
            }

            // 3. Son Çeyrek Net Kâr
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 46
                radius: Theme.radiusSm
                color: Theme.bgInput
                border.color: Theme.borderSubtle
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 8

                    ModernIcon {
                        name: "coins"
                        size: 14
                        color: Theme.bullGreen
                    }

                    ColumnLayout {
                        spacing: 1
                        Text {
                            text: Strings.revLastQuarterNetIncome
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                            color: Theme.textMuted
                        }
                        Text {
                            text: root.ctrl ? root.ctrl.latestQuarterNetIncome : "—"
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.Bold
                            color: Theme.textPrimary
                        }
                    }
                }
            }

            // 4. Net Kâr Marjı
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 46
                radius: Theme.radiusSm
                color: Theme.bgInput
                border.color: Theme.borderSubtle
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 8

                    ModernIcon {
                        name: "percent"
                        size: 14
                        color: "#f59e0b"
                    }

                    ColumnLayout {
                        spacing: 1
                        Text {
                            text: Strings.revNetIncomeMargin
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                            color: Theme.textMuted
                        }
                        Text {
                            text: root.ctrl ? root.ctrl.latestQuarterMargin : "—"
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.Bold
                            color: "#f59e0b"
                        }
                    }
                }
            }
        }
    }
}
