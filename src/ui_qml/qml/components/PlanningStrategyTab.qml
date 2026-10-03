import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import QtWebEngine
import "../theme"

// Strateji Testi: periyodik yeniden dengeleme (eşit / Markowitz) ve stop-loss / take-profit backtest'i.
Item {
    id: root

    property bool rebalanceMode: true
    property string statusText: ""
    property bool statusIsError: false

    readonly property var ctl: (typeof strategyBacktestController !== "undefined") ? strategyBacktestController : null
    readonly property bool running: ctl ? ctl.isRunning : false
    readonly property bool hasResult: ctl ? ctl.hasResult : false
    readonly property var intervalMonths: [1, 3, 6, 12]

    function todayIso() {
        const d = new Date()
        return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0")
    }

    function run() {
        if (!ctl) return
        root.statusText = ""
        if (rebalanceMode) {
            ctl.runRebalancing(txtTickers.text, txtCapital.text, txtStart.text, txtEnd.text,
                               intervalMonths[cmbInterval.currentIndex],
                               cmbWeighting.currentIndex === 1 ? "markowitz" : "equal", txtCommission.text)
        } else {
            ctl.runStopTake(txtTickers.text, txtCapital.text, txtStart.text, txtEnd.text,
                            txtStop.text, txtTake.text, txtCommission.text)
        }
    }

    Connections {
        target: root.ctl
        function onNotification(success, message) {
            root.statusText = message
            root.statusIsError = !success
        }
        function onResultChanged() {
            if (root.ctl.chartHtml !== "") {
                chartView.loadHtml(root.ctl.chartHtml)
            }
        }
    }

    Flickable {
        anchors.fill: parent
        contentWidth: width
        contentHeight: column.implicitHeight
        clip: true
        ScrollBar.vertical: ModernScrollBar {}

        ColumnLayout {
            id: column
            width: parent.width
            spacing: Theme.spaceMd

            // Strateji türü
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                ModernButton {
                    text: Strings.strategyModeRebalance
                    variant: root.rebalanceMode ? "primary" : "secondary"
                    onClicked: root.rebalanceMode = true
                }
                ModernButton {
                    text: Strings.strategyModeStopTake
                    variant: root.rebalanceMode ? "secondary" : "primary"
                    onClicked: root.rebalanceMode = false
                }
                Item { Layout.fillWidth: true }
            }

            // Parametre formu
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: formFlow.implicitHeight + Theme.spaceMd * 2
                color: Theme.bgCard
                radius: Theme.radiusMd
                border.color: Theme.borderCard
                border.width: 1

                Flow {
                    id: formFlow
                    anchors.fill: parent
                    anchors.margins: Theme.spaceMd
                    spacing: Theme.spaceMd

                    ColumnLayout {
                        width: 200
                        spacing: 2
                        Text { text: Strings.strategyTickersLabel; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs }
                        ModernInput { id: txtTickers; Layout.fillWidth: true; text: "THYAO ASELS BIMAS" }
                    }
                    ColumnLayout {
                        width: 150
                        spacing: 2
                        Text { text: Strings.strategyCapitalLabel; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs }
                        ModernInput { id: txtCapital; Layout.fillWidth: true; text: "100000"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
                    }
                    ColumnLayout {
                        width: 120
                        spacing: 2
                        Text { text: Strings.strategyStartLabel; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs }
                        ModernInput { id: txtStart; Layout.fillWidth: true; text: "2023-01-02" }
                    }
                    ColumnLayout {
                        width: 120
                        spacing: 2
                        Text { text: Strings.strategyEndLabel; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs }
                        ModernInput { id: txtEnd; Layout.fillWidth: true; text: root.todayIso() }
                    }
                    ColumnLayout {
                        visible: root.rebalanceMode
                        width: 150
                        spacing: 2
                        Text { text: Strings.strategyIntervalLabel; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs }
                        ModernComboBox {
                            id: cmbInterval
                            Layout.fillWidth: true
                            currentIndex: 1
                            model: [Strings.strategyIntervalMonthly, Strings.strategyIntervalQuarterly,
                                    Strings.strategyIntervalSemiannual, Strings.strategyIntervalYearly]
                        }
                    }
                    ColumnLayout {
                        visible: root.rebalanceMode
                        width: 210
                        spacing: 2
                        Text { text: Strings.strategyWeightingLabel; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs }
                        ModernComboBox {
                            id: cmbWeighting
                            Layout.fillWidth: true
                            model: [Strings.strategyWeightEqual, Strings.strategyWeightMarkowitz]
                        }
                    }
                    ColumnLayout {
                        visible: !root.rebalanceMode
                        width: 110
                        spacing: 2
                        Text { text: Strings.strategyStopLabel; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs }
                        ModernInput { id: txtStop; Layout.fillWidth: true; text: "10"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
                    }
                    ColumnLayout {
                        visible: !root.rebalanceMode
                        width: 110
                        spacing: 2
                        Text { text: Strings.strategyTakeLabel; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs }
                        ModernInput { id: txtTake; Layout.fillWidth: true; text: "30"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
                    }
                    ColumnLayout {
                        width: 100
                        spacing: 2
                        Text { text: Strings.strategyCommissionLabel; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs }
                        ModernInput { id: txtCommission; Layout.fillWidth: true; text: "0"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
                    }
                    ColumnLayout {
                        spacing: 2
                        Item { width: 1; height: Theme.fontXs + 2 }
                        ModernButton {
                            text: root.running ? Strings.btnCalculating : Strings.strategyBtnRun
                            iconName: "play"
                            variant: "primary"
                            enabled: !root.running && root.ctl !== null
                            onClicked: root.run()
                        }
                    }
                }
            }

            Text {
                visible: root.statusText !== ""
                text: root.statusText
                color: root.statusIsError ? Theme.bearRed : Theme.bullGreen
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            // KPI şeridi
            GridLayout {
                visible: root.hasResult
                Layout.fillWidth: true
                columns: root.width < 900 ? 2 : 4
                columnSpacing: Theme.spaceMd
                rowSpacing: Theme.spaceMd
                uniformCellWidths: true

                Repeater {
                    model: root.hasResult ? [
                        { label: Strings.strategyKpiStrategy, value: root.ctl.strategyReturnText, sub: root.ctl.strategyValueText, tint: "" },
                        { label: Strings.strategyKpiBaseline, value: root.ctl.baselineReturnText, sub: root.ctl.baselineValueText, tint: "" },
                        { label: Strings.strategyKpiDifference, value: root.ctl.differenceText, sub: "", tint: root.ctl.differencePositive ? "up" : "down" },
                        { label: Strings.strategyKpiDrawdown, value: root.ctl.drawdownText + " / " + root.ctl.baselineDrawdownText, sub: "", tint: "" }
                    ] : []

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 76
                        color: Theme.bgCard
                        radius: Theme.radiusMd
                        border.color: Theme.borderCard
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: Theme.spaceMd
                            spacing: 2
                            Text { text: modelData.label; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm; elide: Text.ElideRight; Layout.fillWidth: true }
                            Text {
                                text: modelData.value
                                color: modelData.tint === "up" ? Theme.bullGreen : (modelData.tint === "down" ? Theme.bearRed : Theme.textPrimary)
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontLg
                                font.weight: Font.Bold
                            }
                            Text { visible: modelData.sub !== ""; text: modelData.sub; color: Theme.textSecondary; font.family: Theme.fontMono; font.pixelSize: Theme.fontXs }
                        }
                    }
                }
            }

            Text {
                visible: root.hasResult
                text: root.ctl ? root.ctl.summaryText : ""
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            // Grafik
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 380
                color: Theme.bgCard
                radius: Theme.radiusMd
                border.color: Theme.borderCard
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spaceMd
                    spacing: Theme.spaceSm

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm
                        ModernIcon { name: "trendingup"; color: Theme.bullGreen; size: 16 }
                        Text {
                            text: Strings.strategyChartTitle
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.DemiBold
                            Layout.fillWidth: true
                        }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderSubtle }

                    Item {
                        Layout.fillWidth: true
                        Layout.fillHeight: true

                        WebEngineView {
                            id: chartView
                            anchors.fill: parent
                            backgroundColor: Theme.bgCard
                            visible: root.hasResult
                            settings.javascriptEnabled: true
                            settings.localContentCanAccessRemoteUrls: true
                            onVisibleChanged: {
                                if (visible && root.ctl && root.ctl.chartHtml !== "") {
                                    chartView.loadHtml(root.ctl.chartHtml)
                                }
                            }
                        }

                        ColumnLayout {
                            anchors.centerIn: parent
                            visible: !root.hasResult && !root.running
                            spacing: Theme.spaceSm
                            ModernIcon { Layout.alignment: Qt.AlignHCenter; name: "areachart"; color: Theme.textMuted; size: 44 }
                            Text {
                                Layout.alignment: Qt.AlignHCenter
                                text: Strings.strategyNotRunTitle
                                color: Theme.textPrimary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontBase
                                font.weight: Font.DemiBold
                            }
                            Text {
                                Layout.alignment: Qt.AlignHCenter
                                text: Strings.strategyNotRunHint
                                color: Theme.textMuted
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSm
                            }
                        }
                    }
                }
            }

            // Olaylar
            Rectangle {
                visible: root.hasResult
                Layout.fillWidth: true
                Layout.preferredHeight: 260
                color: Theme.bgCard
                radius: Theme.radiusMd
                border.color: Theme.borderCard
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spaceMd
                    spacing: Theme.spaceSm

                    Text {
                        text: Strings.strategyEventsTitle
                        color: Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        font.weight: Font.Bold
                    }

                    Text {
                        visible: root.ctl && root.ctl.events.length === 0
                        text: Strings.strategyEventsEmpty
                        color: Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                    }

                    ListView {
                        id: eventList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 4
                        model: root.ctl ? root.ctl.events : []
                        ScrollBar.vertical: ModernScrollBar {}

                        delegate: Rectangle {
                            width: eventList.width
                            height: 34
                            radius: Theme.radiusSm
                            color: Theme.bgSecondary

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: Theme.spaceSm
                                anchors.rightMargin: Theme.spaceSm
                                spacing: Theme.spaceMd

                                Text { text: modelData.dateText; color: Theme.textSecondary; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm }
                                Text {
                                    text: modelData.actionText
                                    color: modelData.action === "STOP_LOSS" ? Theme.bearRed : (modelData.action === "TAKE_PROFIT" ? Theme.bullGreen : (modelData.action === "FALLBACK" ? Theme.warning : Theme.accent))
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSm
                                    font.weight: Font.DemiBold
                                    Layout.preferredWidth: 90
                                }
                                Text {
                                    text: modelData.detail
                                    color: Theme.textPrimary
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSm
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                            }
                        }
                    }
                }
            }

            Text {
                text: Strings.strategyAssumptions
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Item { Layout.preferredHeight: Theme.spaceMd }
        }
    }
}
