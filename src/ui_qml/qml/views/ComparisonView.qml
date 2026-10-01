import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    id: root

    Component.onCompleted: {
        comparisonController.loadAssetOptions()
        comparisonController.runComparison()
    }

    RowLayout {
        anchors.fill: parent
        spacing: Theme.spaceMd

        // Sol Panel: Varlık Seçim Listesi (280px)
        Rectangle {
            Layout.preferredWidth: 280
            Layout.minimumWidth: 240
            Layout.maximumWidth: 320
            Layout.fillHeight: true
            color: Theme.bgCard
            radius: Theme.radiusMd
            border.color: Theme.borderCard
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Theme.spaceMd
                spacing: Theme.spaceSm

                // Panel Başlığı
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceSm

                    ModernIcon {
                        name: "layers"
                        color: Theme.accent
                        size: 16
                    }

                    Text {
                        text: Strings.compareAssetsTitle
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        font.weight: Font.DemiBold
                        font.letterSpacing: 0.5
                        Layout.fillWidth: true
                    }

                    Text {
                        text: comparisonController.selectedAssets.length + " seçili"
                        color: Theme.accent
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        font.weight: Font.DemiBold
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.borderSubtle
                }

                // Varlıklar Listesi
                ListView {
                    id: assetListView
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: 4
                    model: comparisonController.assetOptions

                    ScrollBar.vertical: ModernScrollBar {}

                    delegate: Rectangle {
                        width: assetListView.width
                        height: 38
                        radius: Theme.radiusSm

                        readonly property bool isSelected: comparisonController.selectedAssets.indexOf(modelData.code) !== -1

                        color: isSelected ? Theme.accentSoft : (itemMouse.containsMouse ? Theme.bgCardHover : Theme.bgSecondary)
                        border.color: isSelected ? Theme.accent : Theme.borderSubtle
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.spaceSm
                            anchors.rightMargin: Theme.spaceSm
                            spacing: Theme.spaceSm

                            // Seçim Kutucuğu
                            Rectangle {
                                width: 18
                                height: 18
                                radius: 4
                                color: isSelected ? Theme.accent : "transparent"
                                border.color: isSelected ? Theme.accent : Theme.textMuted
                                border.width: 1.5

                                ModernIcon {
                                    anchors.centerIn: parent
                                    name: "check"
                                    color: Theme.textInverse
                                    size: 11
                                    visible: isSelected
                                }
                            }

                            Text {
                                text: modelData.label
                                color: isSelected ? Theme.accent : Theme.textPrimary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontBase
                                font.weight: isSelected ? Font.DemiBold : Font.Normal
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }

                            // Varlık Türü Rozeti
                            Rectangle {
                                height: 18
                                width: kindText.width + 8
                                radius: Theme.radiusXs
                                color: Theme.bgPrimary

                                Text {
                                    id: kindText
                                    anchors.centerIn: parent
                                    text: modelData.kind || "VARLIK"
                                    color: Theme.textMuted
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 9
                                    font.weight: Font.DemiBold
                                }
                            }
                        }

                        MouseArea {
                            id: itemMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                comparisonController.toggleAsset(modelData.code, !isSelected)
                                comparisonController.runComparison()
                            }
                        }
                    }
                }

                // Alt Aksiyon Butonu
                Rectangle {
                    Layout.fillWidth: true
                    height: 38
                    radius: Theme.radiusSm
                    color: btnRunMouse.containsMouse ? Theme.accentHover : Theme.accent

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: Theme.spaceXs

                        ModernIcon {
                            name: "refresh"
                            color: Theme.textInverse
                            size: 14
                        }

                        Text {
                            text: Strings.compareBtnRun
                            color: Theme.textInverse
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBase
                            font.weight: Font.DemiBold
                        }
                    }

                    MouseArea {
                        id: btnRunMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: comparisonController.runComparison()
                    }
                }
            }
        }

        // Sağ Panel: Grafik + Metrik Tablosu
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.spaceMd

            // Performans Grafiği Kartı
            ComparisonChartCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 320
            }

            // Risk-Getiri Metrik Tablosu Kartı
            ComparisonMetricsTable {
                Layout.fillWidth: true
                Layout.preferredHeight: 180
                Layout.minimumHeight: 140
            }
        }
    }
}
