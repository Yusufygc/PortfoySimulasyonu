import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import QtWebEngine
import "../theme"
import "../components"

Rectangle {
    id: root

    color: Theme.bgPrimary

    // Dar pencerede parametre paneli üstte, sonuçlar altta (ana sayfa kaydırması devreye girer)
    readonly property bool stacked: width < 980
    readonly property int minContentHeight: stacked ? 1300 : 0

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spaceLg
        spacing: Theme.spaceMd

        // 1. Sayfa Başlığı ve Açıklama
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            Rectangle {
                width: 38
                height: 38
                radius: Theme.radiusMd
                color: Theme.accentSoft

                ModernIcon {
                    anchors.centerIn: parent
                    name: "optimization"
                    size: 20
                    color: Theme.accent
                }
            }

            ColumnLayout {
                spacing: 2

                Text {
                    text: Strings.optTitle
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXl
                    font.weight: Font.Bold
                }

                Text {
                    text: Strings.optSubtitle
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                }
            }

            Item { Layout.fillWidth: true }
        }

        // 2. Ana Çalışma Alanı (Sol Panel: Parametreler | Sağ Panel: KPI + Grafikler/Tablolar)
        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: root.stacked ? 1 : 2
            columnSpacing: Theme.spaceMd
            rowSpacing: Theme.spaceMd

            OptimizationParamsPanel {
                id: paramsPanel
                stacked: root.stacked
                onRiskQuestionnaireRequested: riskQuestionnaire.open()
            }

            // SAĞ ANA ALAN (KPI + Sekmeler + Grafik / Tablo)
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredHeight: 780
                spacing: Theme.spaceMd

                OptimizationKpiStrip {
                    Layout.fillWidth: true
                    stacked: root.stacked
                    hostWidth: root.width
                }

                OptimizationResultsPanel {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                }
            }
        }
    }

    RiskQuestionnaireDialog {
        id: riskQuestionnaire
    }
}
