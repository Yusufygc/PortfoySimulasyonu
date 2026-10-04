import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Hisse bazlı yapay zeka model analizi: tahmin, yön beklentisi, performans, XAI, akran ve tahmin noktaları.
Item {
    id: root

    readonly property bool hasController: typeof modelAnalysisController !== "undefined" && modelAnalysisController
    readonly property var analysis: hasController ? modelAnalysisController.result : ({})
    readonly property bool hasResult: hasController && modelAnalysisController.hasResult
    readonly property bool busy: hasController && modelAnalysisController.isBusy

    signal sendToAdvisorRequested(string prompt)

    function bannerColor(state) {
        if (state === "success") return Theme.bullGreen
        if (state === "error") return Theme.bearRed
        return Theme.warning
    }

    function submit() {
        const ticker = txtTicker.text.trim()
        if (hasController && ticker !== "") modelAnalysisController.analyze(ticker)
    }

    Connections {
        target: root.hasController ? modelAnalysisController : null
        function onAdvisorPromptReady(prompt) { root.sendToAdvisorRequested(prompt) }
    }

    ScrollView {
        anchors.fill: parent
        clip: true
        contentWidth: availableWidth

        ColumnLayout {
            width: parent.width
            spacing: Theme.spaceMd

            // Ticker girişi
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm

                ModernInput {
                    id: txtTicker
                    Layout.preferredWidth: 220
                    placeholder: Strings.mdlTickerPlaceholder
                    onAccepted: root.submit()
                    onTextEdited: text = text.toUpperCase()
                }
                ModernButton {
                    text: Strings.mdlAnalyze
                    variant: "primary"
                    enabled: root.hasController && modelAnalysisController.serviceAvailable && !root.busy && txtTicker.text.trim() !== ""
                    onClicked: root.submit()
                }
                BusyIndicator {
                    running: root.busy
                    visible: running
                    implicitWidth: 24
                    implicitHeight: 24
                }
                Item { Layout.fillWidth: true }
            }

            // Durum / demo uyarısı
            Rectangle {
                Layout.fillWidth: true
                visible: root.hasController && modelAnalysisController.bannerText !== ""
                implicitHeight: bannerText.implicitHeight + Theme.spaceSm * 2
                radius: Theme.radiusSm
                color: Theme.bgSecondary
                border.color: root.hasController ? root.bannerColor(modelAnalysisController.bannerState) : Theme.borderSubtle
                border.width: 1

                Text {
                    id: bannerText
                    anchors.fill: parent
                    anchors.margins: Theme.spaceSm
                    text: root.hasController ? modelAnalysisController.bannerText : ""
                    color: root.hasController ? root.bannerColor(modelAnalysisController.bannerState) : Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    font.weight: Font.DemiBold
                    wrapMode: Text.WordWrap
                    verticalAlignment: Text.AlignVCenter
                }
            }

            Text {
                visible: !root.hasResult && !root.busy
                text: Strings.mdlEmpty
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            // Tahmin + Yön kartları
            GridLayout {
                visible: root.hasResult
                Layout.fillWidth: true
                columns: width > 760 ? 2 : 1
                columnSpacing: Theme.spaceMd
                rowSpacing: Theme.spaceMd

                ModernCard {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    implicitHeight: predictionColumn.implicitHeight + Theme.spaceLg * 2

                    ColumnLayout {
                        id: predictionColumn
                        anchors.fill: parent
                        anchors.margins: Theme.spaceLg
                        spacing: Theme.spaceSm

                        Text { text: Strings.mdlPrediction + " - " + (root.analysis.ticker || ""); color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.Bold }
                        Text { text: root.analysis.predictedText || "-"; color: Theme.textPrimary; font.family: Theme.monoFontFamily; font.pixelSize: 28; font.weight: Font.Bold }
                        Text {
                            visible: root.analysis.hasChange === true
                            text: (root.analysis.changeText || "") + "  (" + Strings.mdlVsLastClose + " " + (root.analysis.lastCloseText || "-") + ")"
                            color: root.analysis.changeIsUp ? Theme.bullGreen : Theme.bearRed
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.DemiBold
                        }
                        Text { text: Strings.mdlInterval + ": " + (root.analysis.intervalText || "-"); color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm }
                        Text { text: Strings.mdlHorizon + ": " + (root.analysis.horizonText || "-") + "   " + Strings.mdlWeekly + ": " + (root.analysis.weeklyReturnText || "-"); color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm }
                        Text { text: Strings.mdlModel + ": " + (root.analysis.modelName || "-") + " (" + (root.analysis.modelFamily || "-") + ")"; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        Text { text: root.analysis.freshnessText || ""; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spaceSm
                            Text { text: Strings.mdlConfidence + ": " + (root.analysis.confidenceText || "-"); color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm }
                            ProgressBar { Layout.fillWidth: true; from: 0; to: 100; value: root.analysis.confidencePct || 0 }
                        }
                        Repeater {
                            model: root.analysis.confidenceWarnings || []
                            Text { text: modelData; color: Theme.warning; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        }
                    }
                }

                ModernCard {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    implicitHeight: outlookColumn.implicitHeight + Theme.spaceLg * 2

                    ColumnLayout {
                        id: outlookColumn
                        anchors.fill: parent
                        anchors.margins: Theme.spaceLg
                        spacing: Theme.spaceSm

                        Text { text: Strings.mdlOutlook; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.Bold }
                        Text {
                            text: root.analysis.outlookText || "-"
                            color: root.analysis.outlookState === "up" ? Theme.bullGreen : (root.analysis.outlookState === "down" ? Theme.bearRed : Theme.textPrimary)
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontLg
                            font.weight: Font.Bold
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spaceSm
                            Text { text: Strings.mdlStrength; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm }
                            ProgressBar { Layout.fillWidth: true; from: 0; to: 100; value: root.analysis.outlookStrengthPct || 0 }
                        }
                        Text { visible: (root.analysis.trendText || "") !== ""; text: root.analysis.trendText || ""; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm }

                        // Performans metrikleri
                        Text { text: Strings.mdlPerformance; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.Bold; Layout.topMargin: Theme.spaceSm }
                        GridLayout {
                            columns: 2
                            columnSpacing: Theme.spaceLg
                            rowSpacing: 4
                            Layout.fillWidth: true
                            Repeater {
                                model: root.analysis.performance || []
                                RowLayout {
                                    Layout.fillWidth: true
                                    Text { text: modelData.label; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; Layout.fillWidth: true }
                                    Text { text: modelData.valueText; color: Theme.textPrimary; font.family: Theme.monoFontFamily; font.pixelSize: Theme.fontXs }
                                }
                            }
                        }
                    }
                }
            }

            // XAI
            ModernCard {
                visible: root.hasResult && root.analysis.xaiAvailable === true
                Layout.fillWidth: true
                implicitHeight: xaiColumn.implicitHeight + Theme.spaceLg * 2

                ColumnLayout {
                    id: xaiColumn
                    anchors.fill: parent
                    anchors.margins: Theme.spaceLg
                    spacing: Theme.spaceSm

                    Text { text: Strings.mdlXai + (root.analysis.xaiMethod ? " (" + root.analysis.xaiMethod + ")" : ""); color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.Bold }
                    Text { visible: (root.analysis.xaiText || "") !== ""; text: root.analysis.xaiText || ""; color: Theme.textPrimary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm; wrapMode: Text.WordWrap; Layout.fillWidth: true }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: width > 560 ? 2 : 1
                        columnSpacing: Theme.spaceLg
                        rowSpacing: Theme.spaceSm

                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignTop
                            spacing: 4
                            Text { text: Strings.mdlXaiPositive; color: Theme.bullGreen; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm; font.weight: Font.DemiBold }
                            Repeater {
                                model: root.analysis.xaiPositive || []
                                RowLayout {
                                    Layout.fillWidth: true
                                    Text { text: modelData.label; color: Theme.textPrimary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; elide: Text.ElideRight; Layout.fillWidth: true }
                                    Text { text: modelData.importanceText; color: Theme.textMuted; font.family: Theme.monoFontFamily; font.pixelSize: Theme.fontXs }
                                }
                            }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignTop
                            spacing: 4
                            Text { text: Strings.mdlXaiNegative; color: Theme.bearRed; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm; font.weight: Font.DemiBold }
                            Repeater {
                                model: root.analysis.xaiNegative || []
                                RowLayout {
                                    Layout.fillWidth: true
                                    Text { text: modelData.label; color: Theme.textPrimary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; elide: Text.ElideRight; Layout.fillWidth: true }
                                    Text { text: modelData.importanceText; color: Theme.textMuted; font.family: Theme.monoFontFamily; font.pixelSize: Theme.fontXs }
                                }
                            }
                        }
                    }
                    Text { visible: (root.analysis.xaiCaveat || "") !== ""; text: root.analysis.xaiCaveat || ""; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                }
            }

            // Akran (peer)
            ModernCard {
                visible: root.hasResult && root.analysis.peer !== undefined && root.analysis.peer.available === true
                Layout.fillWidth: true
                implicitHeight: peerColumn.implicitHeight + Theme.spaceLg * 2

                ColumnLayout {
                    id: peerColumn
                    anchors.fill: parent
                    anchors.margins: Theme.spaceLg
                    spacing: Theme.spaceXs

                    Text { text: Strings.mdlPeer; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.Bold }
                    Text { text: (root.analysis.peer ? root.analysis.peer.labelText : "") + "   " + Strings.mdlPercentile + ": " + (root.analysis.peer ? root.analysis.peer.percentileText : "-") + "   (" + (root.analysis.peer ? root.analysis.peer.universeText : "-") + ")"; color: Theme.textPrimary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Text { text: Strings.mdlProbUp + ": " + (root.analysis.peer ? root.analysis.peer.probUpText : "-") + "   " + Strings.mdlBand + ": " + (root.analysis.peer ? root.analysis.peer.bandText : "-"); color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Repeater {
                        model: (root.analysis.peer && root.analysis.peer.warnings) ? root.analysis.peer.warnings : []
                        Text { text: modelData; color: Theme.warning; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    }
                }
            }

            // Tahmin noktaları
            ModernCard {
                visible: root.hasResult && (root.analysis.forecastPoints || []).length > 0
                Layout.fillWidth: true
                implicitHeight: pointsColumn.implicitHeight + Theme.spaceLg * 2

                ColumnLayout {
                    id: pointsColumn
                    anchors.fill: parent
                    anchors.margins: Theme.spaceLg
                    spacing: 4

                    Text { text: Strings.mdlForecastPoints; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.Bold }
                    Repeater {
                        model: root.analysis.forecastPoints || []
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spaceMd
                            Text { text: modelData.date; color: Theme.textSecondary; font.family: Theme.monoFontFamily; font.pixelSize: Theme.fontXs; Layout.preferredWidth: 90 }
                            Text { text: modelData.closeText; color: Theme.textPrimary; font.family: Theme.monoFontFamily; font.pixelSize: Theme.fontXs; Layout.preferredWidth: 100 }
                            Text { text: modelData.returnText; color: Theme.textSecondary; font.family: Theme.monoFontFamily; font.pixelSize: Theme.fontXs; Layout.preferredWidth: 80 }
                            Text { text: modelData.rangeText; color: Theme.textMuted; font.family: Theme.monoFontFamily; font.pixelSize: Theme.fontXs; Layout.fillWidth: true }
                        }
                    }
                }
            }

            RowLayout {
                visible: root.hasResult
                Layout.fillWidth: true
                spacing: Theme.spaceSm

                Text {
                    text: root.hasController ? modelAnalysisController.disclaimer : ""
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
                ModernButton {
                    text: Strings.mdlSendToAdvisor
                    variant: "secondary"
                    onClicked: modelAnalysisController.sendToAdvisor()
                }
            }

            Item { Layout.preferredHeight: Theme.spaceMd }
        }
    }
}
