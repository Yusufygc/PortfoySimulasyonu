import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Hisse 360 > KAP Ortaklık Yapısı görünümü: KPI şeridi, ortaklık pastası ve zaman çizelgesi.
ColumnLayout {
    id: root
    readonly property var ctrl: (typeof stock360Controller !== "undefined") ? stock360Controller : null
    property real hostWidth: 0
    width: root.hostWidth
    spacing: Theme.spaceMd

    // 1. ÜST KPI STRIP (4 RASYONEL KART)
    GridLayout {
        Layout.fillWidth: true
        columns: 4
        rowSpacing: Theme.spaceSm
        columnSpacing: Theme.spaceSm

        // Kart 1: Ödenmiş Sermaye
        RatioCard {
            title: Strings.labelPaidCapital
            value: root.ctrl ? root.ctrl.paidCapital : "—"
            subtitle: Strings.labelPaidCapitalDesc
            iconName: "coins"
            accentColor: Theme.accent
            badgeText: Strings.badgeNominal
        }

        // Kart 2: Fiili Dolaşımdaki Paylar
        RatioCard {
            title: Strings.labelFreeFloat
            value: root.ctrl ? root.ctrl.freeFloatRatio : "—"
            subtitle: Strings.labelFreeFloatDesc
            iconName: "users"
            accentColor: "#06b6d4"
            badgeText: Strings.badgeFreeFloat
        }

        // Kart 3: Hakim Ortak & Blok Pay
        RatioCard {
            title: Strings.labelControllingShareholder
            value: {
                if (!root.ctrl) return "—";
                var ff = root.ctrl.freeFloatPct || 0.0;
                if (ff <= 0.0 || ff >= 1.0) return "—";
                return "%" + ((1.0 - ff) * 100.0).toFixed(2);
            }
            subtitle: Strings.labelControllingShareholderDesc
            iconName: "target"
            accentColor: "#8b5cf6"
            badgeText: Strings.badgeBlockShare
        }

        // Kart 4: Toplam Bildirim & Senkronizasyon
        ModernCard {
            Layout.fillWidth: true
            implicitHeight: 88

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Theme.spaceSm
                spacing: 4

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6

                    Rectangle {
                        width: 22
                        height: 22
                        radius: Theme.radiusSm
                        color: Qt.rgba(245/255, 158/255, 11/255, 0.15)
                        Layout.alignment: Qt.AlignVCenter

                        ModernIcon {
                            anchors.centerIn: parent
                            name: "history"
                            size: 11
                            color: "#f59e0b"
                        }
                    }

                    Text {
                        text: Strings.labelTotalFilings
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        font.weight: Font.Medium
                        color: Theme.textSecondary
                        Layout.fillWidth: true
                    }

                    ModernButton {
                        text: Strings.btnSyncKap
                        iconName: "refresh"
                        variant: "primary"
                        onClicked: {
                            if (root.ctrl) root.ctrl.refreshShareholdersHistory()
                        }
                    }
                }

                Text {
                    text: Strings.kapSnapshotCountTmpl.arg(root.ctrl ? root.ctrl.kapSnapshotCount : 0)
                    font.family: Theme.fontMono
                    font.pixelSize: Theme.fontLg
                    font.weight: Font.Bold
                    color: Theme.textPrimary
                }

                Text {
                    text: Strings.labelLastKapUpdate + ": " + (root.ctrl ? root.ctrl.lastKapFilingDate : "—")
                    font.family: Theme.fontFamily
                    font.pixelSize: 10
                    color: Theme.textMuted
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }
        }
    }

    // 2. ORTA BÖLÜM: 2 SÜTUNLU FINTECH DİSCLOSURE MERKEZİ
    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.spaceMd

        // Sol: Ortaklık Dağılımı Donut Kartı (Genişletilmiş fullView modu)
        ShareholderPieCard {
            fullView: true
            Layout.fillWidth: true
            Layout.preferredWidth: 440
            Layout.minimumWidth: 360
        }

        // Sağ: Kronolojik Pay Değişim Zaman Çizelgesi (Filtre ve Arama destekli)
        FintechShareholderTimeline {
            Layout.fillWidth: true
            Layout.preferredWidth: 560
            Layout.minimumWidth: 420
        }
    }
}
