import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Ayarlar > Veri Sağlığı ve Senkronizasyon: bütünlük kontrolü ve çift motor senkronu.
ColumnLayout {
    Layout.fillWidth: true
    spacing: 16

    Text {
        text: Strings.settingsDbStatsTitle
        color: Theme.textMuted
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontXs
        font.weight: Font.Bold
        font.letterSpacing: 0.5
    }

    // Çift Motor Kartları Yan Yana
    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.spaceMd

        // A) SQLite OLTP Kartı
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 290
            radius: Theme.radiusMd
            color: Theme.bgSecondary
            border.color: Theme.borderSubtle
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: Strings.settingsSqliteTitle
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        font.weight: Font.Bold
                        Layout.fillWidth: true
                    }
                    Text {
                        text: (typeof settingsController !== "undefined") ? settingsController.sqliteDbSize : "0 B"
                        color: Theme.bullGreen
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        font.weight: Font.Bold
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.borderSubtle
                }

                Text {
                    Layout.fillWidth: true
                    text: (typeof settingsController !== "undefined") ? settingsController.sqliteDbPath : ""
                    elide: Text.ElideMiddle
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                }

                // Tablo Satır Sayıları
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 6

                    Repeater {
                        model: (typeof settingsController !== "undefined") ? settingsController.sqliteTableStats : []

                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: modelData.name
                                color: Theme.textSecondary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                Layout.fillWidth: true
                            }
                            Text {
                                text: modelData.count + Strings.settingsRecordSuffix
                                color: Theme.textPrimary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                font.weight: Font.DemiBold
                            }
                        }
                    }
                }

                Item { Layout.fillHeight: true }

                // Bütünlük Kontrolü Butonu
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 34
                    radius: Theme.radiusSm
                    color: btnIntegrityMouse.containsMouse ? Theme.bgCardHover : Theme.bgPrimary
                    border.color: Theme.borderSubtle
                    border.width: 1

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 6
                        ModernIcon {
                            iconSource: Icons.shieldCheck
                            size: 14
                            color: Theme.primary
                        }
                        Text {
                            text: Strings.settingsBtnIntegrityCheck
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            font.weight: Font.Medium
                        }
                    }

                    MouseArea {
                        id: btnIntegrityMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (typeof settingsController !== "undefined") {
                                settingsController.checkDatabaseIntegrity()
                            }
                        }
                    }
                }
            }
        }

        // B) DuckDB OLAP Kartı
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 290
            radius: Theme.radiusMd
            color: Theme.bgSecondary
            border.color: Theme.borderSubtle
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: Strings.settingsDuckDbTitle
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        font.weight: Font.Bold
                        Layout.fillWidth: true
                    }
                    Text {
                        text: (typeof settingsController !== "undefined") ? settingsController.duckDbSize : "0 B"
                        color: Theme.primary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        font.weight: Font.Bold
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.borderSubtle
                }

                Text {
                    Layout.fillWidth: true
                    text: (typeof settingsController !== "undefined") ? settingsController.duckDbPath : ""
                    elide: Text.ElideMiddle
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: Strings.settingsDbStockCount; color: Theme.textSecondary; font.pixelSize: Theme.fontXs; Layout.fillWidth: true }
                        Text { text: (typeof settingsController !== "undefined") ? settingsController.duckDbStockCount + " Hisse" : "624 Hisse"; color: Theme.textPrimary; font.weight: Font.DemiBold; font.pixelSize: Theme.fontXs }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: Strings.settingsDbTotalBars; color: Theme.textSecondary; font.pixelSize: Theme.fontXs; Layout.fillWidth: true }
                        Text { text: (typeof settingsController !== "undefined") ? settingsController.duckDbTotalBars + " Bar" : "0 Bar"; color: Theme.textPrimary; font.weight: Font.DemiBold; font.pixelSize: Theme.fontXs }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: Strings.settingsDbLastSync; color: Theme.textSecondary; font.pixelSize: Theme.fontXs; Layout.fillWidth: true }
                        Text { text: (typeof settingsController !== "undefined") ? settingsController.duckDbLastDate : "-"; color: Theme.bullGreen; font.weight: Font.Bold; font.pixelSize: Theme.fontXs }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: Strings.settingsDbAutoSync; color: Theme.textSecondary; font.pixelSize: Theme.fontXs; Layout.fillWidth: true }
                        Text { text: Strings.settingsDbAutoSyncValue; color: Theme.primary; font.weight: Font.DemiBold; font.pixelSize: Theme.fontXs }
                    }
                }

                Item { Layout.fillHeight: true }

                // Şimdi Senkronize Et Butonu
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 34
                    radius: Theme.radiusSm
                    color: (typeof settingsController !== "undefined" && settingsController.isSyncing)
                           ? Theme.bgCardHover
                           : (btnSyncMouse.containsMouse ? Theme.primaryHover : Theme.primary)

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 6
                        ModernIcon {
                            iconSource: Icons.refresh
                            size: 14
                            color: "#FFFFFF"
                        }
                        Text {
                            text: (typeof settingsController !== "undefined" && settingsController.isSyncing)
                                  ? "Senkronize Ediliyor..."
                                  : Strings.settingsBtnSyncNow
                            color: "#FFFFFF"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            font.weight: Font.Medium
                        }
                    }

                    MouseArea {
                        id: btnSyncMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        enabled: (typeof settingsController !== "undefined") && !settingsController.isSyncing
                        onClicked: {
                            if (typeof settingsController !== "undefined") {
                                settingsController.runFullMarketSync()
                            }
                        }
                    }
                }
            }
        }
    }

    // Bütünlük Sonuç Notu
    Text {
        visible: (typeof settingsController !== "undefined") && settingsController.integrityCheckResult.length > 0
        text: (typeof settingsController !== "undefined") ? settingsController.integrityCheckResult : ""
        color: Theme.bullGreen
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontXs
        font.weight: Font.Medium
    }
}
