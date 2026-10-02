import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

ModernCard {
    id: root

    readonly property var ctrl: (typeof stock360Controller !== "undefined") ? stock360Controller : null
    property var dupont: (root.ctrl && root.ctrl.dupontData) ? root.ctrl.dupontData : {}

    implicitHeight: 210
    Layout.fillWidth: true

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spaceMd
        spacing: Theme.spaceSm

        // Üst Başlık & ROE Durum Rozeti
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
                        name: "layers"
                        size: 12
                        color: Theme.accent
                    }
                }

                Text {
                    text: Strings.dupontTitle
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    font.weight: Font.Bold
                    color: Theme.textPrimary
                    font.letterSpacing: 0.5
                }
            }

            // ROE Durumu Rozeti
            Rectangle {
                implicitWidth: roeStatusTxt.implicitWidth + 14
                implicitHeight: 22
                radius: 11
                color: Qt.rgba(Theme.bullGreen.r, Theme.bullGreen.g, Theme.bullGreen.b, 0.15)
                border.color: Qt.rgba(Theme.bullGreen.r, Theme.bullGreen.g, Theme.bullGreen.b, 0.3)
                border.width: 1

                Text {
                    id: roeStatusTxt
                    anchors.centerIn: parent
                    text: root.dupont.piotroskiStatus || root.dupont.roe_status || Strings.financialHighEfficiency
                    font.family: Theme.fontFamily
                    font.pixelSize: 10
                    font.weight: Font.DemiBold
                    color: Theme.bullGreen
                }
            }
        }

        // Ayırıcı
        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.borderSubtle
        }

        // Ana İçerik: Sol = DuPont 3 Adımlı Formül Akışı, Sağ = Piotroski F-Score
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.spaceMd

            // Sol Kısım: DuPont Akışı (3 Adım + Sonuç)
            RowLayout {
                Layout.fillWidth: true
                Layout.preferredWidth: 620
                Layout.minimumWidth: 360
                spacing: 6

                // 1. Adım: Net Kâr Marjı
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: Theme.radiusSm
                    color: Theme.bgInput
                    border.color: Theme.borderSubtle
                    border.width: 1

                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 2

                        Text {
                            text: Strings.labelNetMargin
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                            color: Theme.textMuted
                            Layout.alignment: Qt.AlignHCenter
                        }
                        Text {
                            text: root.dupont.netMargin || root.dupont.margin || "—"
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontMd
                            font.weight: Font.Bold
                            color: "#f59e0b"
                            Layout.alignment: Qt.AlignHCenter
                        }
                        Text {
                            text: Strings.dupontProfitEngine
                            font.family: Theme.fontFamily
                            font.pixelSize: 9
                            color: Theme.textMuted
                            Layout.alignment: Qt.AlignHCenter
                        }
                    }
                }

                // Çarpı Operatörü
                Text {
                    text: "×"
                    font.family: Theme.fontFamily
                    font.pixelSize: 16
                    font.weight: Font.Bold
                    color: Theme.textMuted
                    Layout.alignment: Qt.AlignVCenter
                }

                // 2. Adım: Aktif Devir Hızı
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: Theme.radiusSm
                    color: Theme.bgInput
                    border.color: Theme.borderSubtle
                    border.width: 1

                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 2

                        Text {
                            text: Strings.labelAssetTurnover
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                            color: Theme.textMuted
                            Layout.alignment: Qt.AlignHCenter
                        }
                        Text {
                            text: root.dupont.assetTurnover || root.dupont.turnover || "—"
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontMd
                            font.weight: Font.Bold
                            color: Theme.accent
                            Layout.alignment: Qt.AlignHCenter
                        }
                        Text {
                            text: Strings.dupontAssetEfficiency
                            font.family: Theme.fontFamily
                            font.pixelSize: 9
                            color: Theme.textMuted
                            Layout.alignment: Qt.AlignHCenter
                        }
                    }
                }

                // Çarpı Operatörü
                Text {
                    text: "×"
                    font.family: Theme.fontFamily
                    font.pixelSize: 16
                    font.weight: Font.Bold
                    color: Theme.textMuted
                    Layout.alignment: Qt.AlignVCenter
                }

                // 3. Adım: Finansal Kaldıraç
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: Theme.radiusSm
                    color: Theme.bgInput
                    border.color: Theme.borderSubtle
                    border.width: 1

                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 2

                        Text {
                            text: Strings.labelFinancialLeverage
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                            color: Theme.textMuted
                            Layout.alignment: Qt.AlignHCenter
                        }
                        Text {
                            text: root.dupont.financialLeverage || root.dupont.leverage || "—"
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontMd
                            font.weight: Font.Bold
                            color: "#8b5cf6"
                            Layout.alignment: Qt.AlignHCenter
                        }
                        Text {
                            text: Strings.dupontDebtEquity
                            font.family: Theme.fontFamily
                            font.pixelSize: 9
                            color: Theme.textMuted
                            Layout.alignment: Qt.AlignHCenter
                        }
                    }
                }

                // Eşittir Operatörü
                Text {
                    text: "="
                    font.family: Theme.fontFamily
                    font.pixelSize: 16
                    font.weight: Font.Bold
                    color: Theme.textMuted
                    Layout.alignment: Qt.AlignVCenter
                }

                // Sonuç: ROE (Özsermaye Kârlılığı)
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: Theme.radiusSm
                    color: Qt.rgba(Theme.bullGreen.r, Theme.bullGreen.g, Theme.bullGreen.b, 0.12)
                    border.color: Qt.rgba(Theme.bullGreen.r, Theme.bullGreen.g, Theme.bullGreen.b, 0.4)
                    border.width: 1.5

                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 2

                        Text {
                            text: Strings.dupontRoeResult
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                            font.weight: Font.Bold
                            color: Theme.bullGreen
                            Layout.alignment: Qt.AlignHCenter
                        }
                        Text {
                            text: root.dupont.roe || "—"
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontLg
                            font.weight: Font.Bold
                            color: Theme.bullGreen
                            Layout.alignment: Qt.AlignHCenter
                        }
                        Text {
                            text: Strings.dupontEquityProfit
                            font.family: Theme.fontFamily
                            font.pixelSize: 9
                            color: Theme.textMuted
                            Layout.alignment: Qt.AlignHCenter
                        }
                    }
                }
            }

            // Sağ Kısım: Piotroski F-Score Kartı
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredWidth: 300
                Layout.minimumWidth: 180
                Layout.fillHeight: true
                radius: Theme.radiusSm
                color: Theme.bgInput
                border.color: Theme.borderSubtle
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 4

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 6

                        ModernIcon {
                            name: "shield-check"
                            size: 14
                            color: Theme.accent
                        }

                        Text {
                            text: Strings.ratioPiotroski
                            font.family: Theme.fontFamily
                            font.pixelSize: 11
                            font.weight: Font.Bold
                            color: Theme.textPrimary
                        }

                        Item { Layout.fillWidth: true }

                        Text {
                            text: (root.dupont.piotroski && root.dupont.piotroski.indexOf("/") !== -1)
                                  ? root.dupont.piotroski
                                  : ((root.dupont.piotroski || "—") + " / 9")
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontMd
                            font.weight: Font.Bold
                            color: Theme.accent
                        }
                    }

                    Text {
                        text: root.dupont.piotroskiStatus || root.dupont.piotroski_desc || Strings.financialHealthAnalysis
                        font.family: Theme.fontFamily
                        font.pixelSize: 10
                        color: Theme.textMuted
                    }

                    // 9 Segmentli Sağlık Çubuğu
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.topMargin: 4
                        spacing: 3

                        Repeater {
                            model: 9
                            Rectangle {
                                Layout.fillWidth: true
                                height: 6
                                radius: 2
                                property int pVal: parseInt(root.dupont.piotroski) || 0
                                color: (index < pVal)
                                       ? ((pVal >= 7) ? Theme.bullGreen : ((pVal >= 4) ? "#f59e0b" : Theme.bearRed))
                                       : (Theme.isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.08)")
                            }
                        }
                    }
                }
            }
        }
    }
}
