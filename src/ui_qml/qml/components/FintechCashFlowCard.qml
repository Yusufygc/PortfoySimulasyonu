import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

ModernCard {
    id: root

    readonly property var ctrl: (typeof stock360Controller !== "undefined") ? stock360Controller : null
    property var cfData: (root.ctrl && root.ctrl.cashFlowData) ? root.ctrl.cashFlowData : {}

    implicitHeight: 180
    Layout.fillWidth: true

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spaceMd
        spacing: Theme.spaceSm

        // Üst Başlık & Kaldıraç Durum Rozeti
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
                        name: "wallet"
                        size: 12
                        color: Theme.accent
                    }
                }

                Text {
                    text: Strings.cashFlowTitle
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    font.weight: Font.Bold
                    color: Theme.textPrimary
                    font.letterSpacing: 0.5
                }
            }

            // Kaldıraç Durumu Rozeti
            Rectangle {
                implicitWidth: cfStatusTxt.implicitWidth + 14
                implicitHeight: 22
                radius: 11
                color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.15)
                border.color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.3)
                border.width: 1

                Text {
                    id: cfStatusTxt
                    anchors.centerIn: parent
                    text: root.cfData.debtStatus || root.cfData.leverage_status || Strings.financialDebtBalanced
                    font.family: Theme.fontFamily
                    font.pixelSize: 10
                    font.weight: Font.DemiBold
                    color: Theme.accent
                }
            }
        }

        // Ayırıcı
        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.borderSubtle
        }

        // 4'lü Nakit ve Borç Metrik Kutuları
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.spaceSm

            // 1. İşletme Nakit Akımı (OCF)
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
                        text: Strings.labelOperatingCashFlow
                        font.family: Theme.fontFamily
                        font.pixelSize: 10
                        color: Theme.textMuted
                        Layout.alignment: Qt.AlignHCenter
                    }
                    Text {
                        text: root.cfData.operatingCf || root.cfData.ocf || "—"
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontMd
                        font.weight: Font.Bold
                        color: Theme.bullGreen
                        Layout.alignment: Qt.AlignHCenter
                    }
                    Text {
                        text: Strings.cfOperatingInflow
                        font.family: Theme.fontFamily
                        font.pixelSize: 9
                        color: Theme.textMuted
                        Layout.alignment: Qt.AlignHCenter
                    }
                }
            }

            // 2. Yatırım Harcamaları (Capex)
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
                        text: Strings.labelCapex
                        font.family: Theme.fontFamily
                        font.pixelSize: 10
                        color: Theme.textMuted
                        Layout.alignment: Qt.AlignHCenter
                    }
                    Text {
                        text: root.cfData.capex || "—"
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontMd
                        font.weight: Font.Bold
                        color: "#ef4444"
                        Layout.alignment: Qt.AlignHCenter
                    }
                    Text {
                        text: Strings.cfCapacityCapex
                        font.family: Theme.fontFamily
                        font.pixelSize: 9
                        color: Theme.textMuted
                        Layout.alignment: Qt.AlignHCenter
                    }
                }
            }

            // 3. Serbest Nakit Akımı (FCF)
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
                        text: Strings.labelFreeCashFlow
                        font.family: Theme.fontFamily
                        font.pixelSize: 10
                        color: Theme.textMuted
                        Layout.alignment: Qt.AlignHCenter
                    }
                    Text {
                        text: root.cfData.fcf || "—"
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontMd
                        font.weight: Font.Bold
                        color: Theme.bullGreen
                        Layout.alignment: Qt.AlignHCenter
                    }
                    Text {
                        text: Strings.cfFreeCashToEquity
                        font.family: Theme.fontFamily
                        font.pixelSize: 9
                        color: Theme.textMuted
                        Layout.alignment: Qt.AlignHCenter
                    }
                }
            }

            // 4. Net Borç / FAVÖK
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
                        text: Strings.labelNetDebtToEbitda
                        font.family: Theme.fontFamily
                        font.pixelSize: 10
                        color: Theme.textMuted
                        Layout.alignment: Qt.AlignHCenter
                    }
                    Text {
                        text: root.cfData.netDebtEbitda || root.cfData.net_debt_ebitda || "—"
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontMd
                        font.weight: Font.Bold
                        color: "#f59e0b"
                        Layout.alignment: Qt.AlignHCenter
                    }
                    Text {
                        text: Strings.cfNetDebtPrefix + (root.cfData.netDebt || root.cfData.net_debt || "—")
                        font.family: Theme.fontFamily
                        font.pixelSize: 9
                        color: Theme.textMuted
                        Layout.alignment: Qt.AlignHCenter
                    }
                }
            }
        }
    }
}
