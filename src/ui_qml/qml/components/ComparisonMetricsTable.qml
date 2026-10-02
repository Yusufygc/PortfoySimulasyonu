import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

Rectangle {
    id: root

    color: Theme.bgCard
    radius: Theme.radiusMd
    border.color: Theme.borderCard
    border.width: 1

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spaceMd
        spacing: Theme.spaceSm

        // Başlık
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            ModernIcon {
                name: "barchart"
                color: Theme.accent
                size: 16
            }

            Text {
                text: Strings.compareMetricsTitle
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                font.weight: Font.DemiBold
                font.letterSpacing: 0.5
                Layout.fillWidth: true
            }

            Text {
                text: comparisonController.metricsList.length + Strings.compareAssetCountSuffix
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
            }
        }

        // Kolon Başlıkları
        Rectangle {
            Layout.fillWidth: true
            height: 32
            color: Theme.bgSecondary
            radius: Theme.radiusSm

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.spaceSm
                anchors.rightMargin: Theme.spaceSm
                spacing: Theme.spaceSm

                Text {
                    text: Strings.compareThAsset
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.DemiBold
                    Layout.fillWidth: true
                }

                Text {
                    text: Strings.compareThReturn
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.DemiBold
                    horizontalAlignment: Text.AlignRight
                    Layout.preferredWidth: 120
                }

                Text {
                    text: Strings.compareThVolatility
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.DemiBold
                    horizontalAlignment: Text.AlignRight
                    Layout.preferredWidth: 120
                }
            }
        }

        // Metrik Listesi
        ListView {
            id: metricsListView
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 2
            model: comparisonController.metricsList

            ScrollBar.vertical: ModernScrollBar {}

            delegate: Rectangle {
                width: metricsListView.width
                height: 38
                radius: Theme.radiusSm
                color: rowMouse.containsMouse ? Theme.bgCardHover : (index % 2 === 0 ? "transparent" : Theme.bgSecondary)

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.spaceSm
                    anchors.rightMargin: Theme.spaceSm
                    spacing: Theme.spaceSm

                    Text {
                        text: modelData.label
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        font.weight: Font.Medium
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }

                    Text {
                        text: (modelData.totalReturn > 0 ? "+" : "") + modelData.totalReturn.toFixed(2) + " %"
                        color: modelData.totalReturn > 0 ? Theme.bullGreen : (modelData.totalReturn < 0 ? Theme.bearRed : Theme.textMuted)
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontSm
                        font.weight: Font.Bold
                        horizontalAlignment: Text.AlignRight
                        Layout.preferredWidth: 120
                    }

                    Text {
                        text: "%" + modelData.volatility.toFixed(2)
                        color: Theme.textSecondary
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontSm
                        horizontalAlignment: Text.AlignRight
                        Layout.preferredWidth: 120
                    }
                }

                MouseArea {
                    id: rowMouse
                    anchors.fill: parent
                    hoverEnabled: true
                }
            }
        }
    }
}
