import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Hisse 360 > Genel Bakış görünümü: değerleme rasyoları, gelir grafiği + KAP ortaklık ve teknik seviyeler.
ColumnLayout {
    id: root
    readonly property var ctrl: (typeof stock360Controller !== "undefined") ? stock360Controller : null
    property real hostWidth: 0
    width: root.hostWidth
    spacing: Theme.spaceMd

    // 4. ÖNEMLİ DEĞERLEME VE FİNANSAL RASYOLAR (8'Lİ GRID)
    GridLayout {
        Layout.fillWidth: true
        columns: 4
        rowSpacing: Theme.spaceSm
        columnSpacing: Theme.spaceSm

        RatioCard {
            title: Strings.ratioPE
            value: root.ctrl ? root.ctrl.peRatio : "—"
            subtitle: Strings.ratioPEDesc
            iconName: "coins"
            accentColor: Theme.accent
            badgeText: Strings.badgeValuation
        }

        RatioCard {
            title: Strings.ratioPB
            value: root.ctrl ? root.ctrl.pbRatio : "—"
            subtitle: Strings.ratioPBDesc
            iconName: "scale"
            accentColor: "#8b5cf6"
            badgeText: Strings.badgeMultiple
        }

        RatioCard {
            title: Strings.ratioEvEbitda
            value: root.ctrl ? root.ctrl.evEbitda : "—"
            subtitle: Strings.ratioEvEbitdaDesc
            iconName: "activity"
            accentColor: "#06b6d4"
            badgeText: Strings.badgeOperational
        }

        RatioCard {
            title: Strings.ratioDivYield
            value: root.ctrl ? root.ctrl.divYield : "—"
            subtitle: Strings.ratioDivYieldDesc
            iconName: "wallet"
            accentColor: "#ec4899"
            badgeText: Strings.badgeDividend
        }

        RatioCard {
            title: Strings.ratioROE
            value: root.ctrl ? root.ctrl.roe : "—"
            subtitle: Strings.ratioROEDesc
            iconName: "trendingup"
            accentColor: Theme.bullGreen
            badgeText: Strings.badgeProfitability
        }

        RatioCard {
            title: Strings.ratioNetDebtEbitda
            value: root.ctrl ? root.ctrl.netDebtEbitda : "—"
            subtitle: Strings.ratioNetDebtEbitdaDesc
            iconName: "banknote"
            accentColor: "#f59e0b"
            badgeText: Strings.badgeLeverage
        }

        RatioCard {
            title: Strings.ratioPiotroski
            value: root.ctrl ? root.ctrl.piotroskiScore : "—"
            subtitle: Strings.ratioPiotroskiDesc
            iconName: "shield-check"
            accentColor: Theme.accent
            badgeText: Strings.badgeFScore
        }

        RatioCard {
            title: Strings.ratioCurrentRatio
            value: root.ctrl ? root.ctrl.currentRatio : "—"
            subtitle: Strings.ratioCurrentRatioDesc
            iconName: "zap"
            accentColor: "#10b981"
            badgeText: Strings.badgeLiquidity
        }
    }

    // 5. ORTA BÖLÜM: FİNTECH GELİR GRAFİĞİ + KAP ORTAKLIK
    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.spaceMd

        // Çeyreklik Gelir ve Kârlılık Grafiği (Fintech)
        FintechRevenueChart {
            Layout.fillWidth: true
            Layout.preferredWidth: 620
            Layout.minimumWidth: 380
        }

        // KAP Ortaklık Yapısı & Halka Açıklık Oranı
        ShareholderPieCard {
            fullView: false
            Layout.fillWidth: true
            Layout.preferredWidth: 380
            Layout.minimumWidth: 300
        }
    }

    // 6. TEKNİK SEVİYELER & DESTEK / DİRENÇ KARTI
    ModernCard {
        Layout.fillWidth: true
        implicitHeight: techCol.implicitHeight + Theme.spaceMd * 2

        ColumnLayout {
            id: techCol
            anchors.fill: parent
            anchors.margins: Theme.spaceMd
            spacing: Theme.spaceSm

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm

                RowLayout {
                    spacing: 6
                    Layout.fillWidth: true

                    Rectangle {
                        width: 18
                        height: 18
                        radius: Theme.radiusSm
                        color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.15)
                        Layout.alignment: Qt.AlignVCenter

                        ModernIcon {
                            anchors.centerIn: parent
                            name: "target"
                            size: 11
                            color: Theme.accent
                        }
                    }

                    Text {
                        text: Strings.technicalTitle
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        font.weight: Font.Bold
                        color: Theme.textPrimary
                        font.letterSpacing: 0.5
                    }
                }

                Rectangle {
                    implicitWidth: trendLabel.implicitWidth + 14
                    implicitHeight: 22
                    radius: 11
                    color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.15)
                    Layout.alignment: Qt.AlignVCenter

                    Text {
                        id: trendLabel
                        anchors.centerIn: parent
                        text: root.ctrl ? root.ctrl.trendStatus : "Dengeli"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        font.weight: Font.DemiBold
                        color: Theme.accent
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: Theme.borderSubtle
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm

                // RSI (14)
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 64
                    radius: Theme.radiusSm
                    color: Theme.bgInput
                    border.color: Theme.borderSubtle
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 2

                        Text {
                            text: Strings.labelRSI
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            color: Theme.textMuted
                        }

                        RowLayout {
                            spacing: 6
                            Text {
                                text: root.ctrl ? root.ctrl.rsi14 : "—"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSm
                                font.weight: Font.Bold
                                color: Theme.textPrimary
                            }

                            Rectangle {
                                implicitWidth: rsiStatusTxt.implicitWidth + 8
                                implicitHeight: 16
                                radius: 3
                                color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.15)
                                Text {
                                    id: rsiStatusTxt
                                    anchors.centerIn: parent
                                    text: root.ctrl ? root.ctrl.rsiStatus : Strings.stock360Neutral
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 9
                                    font.weight: Font.DemiBold
                                    color: Theme.accent
                                }
                            }
                        }
                    }
                }

                // MACD Sinyal
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 64
                    radius: Theme.radiusSm
                    color: Theme.bgInput
                    border.color: Theme.borderSubtle
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 2

                        Text {
                            text: Strings.labelMACD
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            color: Theme.textMuted
                        }

                        RowLayout {
                            spacing: 4
                            Text {
                                text: (root.ctrl ? root.ctrl.macdLine : "—")
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                font.weight: Font.Bold
                                color: Theme.accent
                            }
                            Text {
                                text: "/ " + (root.ctrl ? root.ctrl.macdSignal : "—")
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                color: Theme.textSecondary
                            }
                        }
                    }
                }

                // SMA 50 / 200
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 64
                    radius: Theme.radiusSm
                    color: Theme.bgInput
                    border.color: Theme.borderSubtle
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 2

                        Text {
                            text: Strings.labelMovingAverages
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            color: Theme.textMuted
                        }

                        RowLayout {
                            spacing: 4
                            Text {
                                text: (root.ctrl ? root.ctrl.sma50 : "—")
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                font.weight: Font.Bold
                                color: Theme.accent
                            }
                            Text {
                                text: "/ " + (root.ctrl ? root.ctrl.sma200 : "—")
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                color: Theme.textSecondary
                            }
                        }
                    }
                }

                // Destek & Direnç
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 64
                    radius: Theme.radiusSm
                    color: Theme.bgInput
                    border.color: Theme.borderSubtle
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 2

                        Text {
                            text: Strings.labelSupport + " / " + Strings.labelResistance
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            color: Theme.textMuted
                        }

                        RowLayout {
                            spacing: 4
                            Text {
                                text: (root.ctrl ? root.ctrl.support : "—")
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                font.weight: Font.Bold
                                color: Theme.bullGreen
                            }
                            Text {
                                text: "/ " + (root.ctrl ? root.ctrl.resistance : "—")
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                font.weight: Font.Bold
                                color: Theme.bearRed
                            }
                        }
                    }
                }
            }
        }
    }
}
