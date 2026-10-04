import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"
import "../components"

Rectangle {
    id: root
    color: "transparent"

    property int activeTabIndex: 0

    Connections {
        target: (typeof settingsController !== "undefined") ? settingsController : null
        function onOperationNotification(success, message) {
            settingsToast.show(message, success)
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spaceMd

        // ---------------------------------------------------------------------
        // 1. ÜST BAŞLIK & SEKME SEÇİCİ BARI
        // ---------------------------------------------------------------------
        Flow {
            Layout.fillWidth: true
            spacing: Theme.spaceMd

            ColumnLayout {
                spacing: 2

                Text {
                    text: Strings.settingsTitle
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXl
                    font.weight: Font.Bold
                }

                Text {
                    text: Strings.settingsSubtitle
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                }
            }

            // Sekme Butonları (6 Sekme)
            Rectangle {
                height: 38
                width: rowTabs.implicitWidth + 8
                radius: Theme.radiusMd
                color: Theme.bgSecondary
                border.color: Theme.borderSubtle
                border.width: 1

                RowLayout {
                    id: rowTabs
                    anchors.centerIn: parent
                    spacing: 4

                    Repeater {
                        model: [
                            { name: Strings.settingsTabAppearance, icon: Icons.sun },
                            { name: Strings.settingsTabApi, icon: Icons.settings },
                            { name: Strings.settingsTabDatabase, icon: Icons.layers },
                            { name: Strings.settingsTabExport, icon: Icons.fileText },
                            { name: Strings.settingsTabCorporate, icon: Icons.layers },
                            { name: Strings.settingsTabPriceData, icon: Icons.history },
                            { name: Strings.settingsTabMarketAdj, icon: Icons.layers },
                            { name: Strings.settingsTabSystem, icon: Icons.settings }
                        ]

                        Rectangle {
                            Layout.preferredHeight: 30
                            Layout.preferredWidth: rowTabItem.implicitWidth + 18
                            radius: Theme.radiusSm
                            color: (root.activeTabIndex === index)
                                   ? Theme.primary
                                   : (tabMouse.containsMouse ? Theme.bgCardHover : "transparent")

                            RowLayout {
                                id: rowTabItem
                                anchors.centerIn: parent
                                spacing: 6

                                ModernIcon {
                                    iconSource: modelData.icon
                                    size: 14
                                    color: (root.activeTabIndex === index) ? "#FFFFFF" : Theme.textSecondary
                                }

                                Text {
                                    text: modelData.name
                                    color: (root.activeTabIndex === index) ? "#FFFFFF" : Theme.textSecondary
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                    font.weight: (root.activeTabIndex === index) ? Font.DemiBold : Font.Normal
                                }
                            }

                            MouseArea {
                                id: tabMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.activeTabIndex = index
                            }
                        }
                    }
                }
            }
        }

        // ---------------------------------------------------------------------
        // 2. ANA İÇERİK ALANI (Aktif Sekme Görünümü)
        // ---------------------------------------------------------------------
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: Theme.radiusMd
            color: Theme.bgCard
            border.color: Theme.borderCard
            border.width: 1

            ScrollView {
                id: mainScroll
                anchors.fill: parent
                anchors.margins: Theme.spaceMd
                clip: true
                ScrollBar.vertical: ModernScrollBar {}

                ColumnLayout {
                    width: mainScroll.availableWidth
                    spacing: Theme.spaceMd

                    // =========================================================
                    // SEKME 0: GÖRÜNÜM & TEMA YÖNETİMİ
                    // =========================================================
                    SettingsAppearanceTab {
                        Layout.fillWidth: true
                        visible: root.activeTabIndex === 0
                    }

                    // =========================================================
                    // SEKME 1: API ANAHTARLARI & ENTEGRASYONLAR
                    // =========================================================
                    SettingsApiKeysTab {
                        Layout.fillWidth: true
                        visible: root.activeTabIndex === 1
                    }

                    // =========================================================
                    // SEKME 2: VERİ SAĞLIĞI & SENKRONİZASYON (ÇİFT MOTOR)
                    // =========================================================
                    SettingsDataHealthTab {
                        Layout.fillWidth: true
                        visible: root.activeTabIndex === 2
                    }

                    // =========================================================
                    // SEKME 3: DIŞA AKTARIM & YEDEKLEME (EXPORT / BACKUP)
                    // =========================================================
                    SettingsExportTab {
                        Layout.fillWidth: true
                        visible: root.activeTabIndex === 3
                    }

                    // =========================================================
                    // SEKME 4: KURUMSAL AKSİYONLAR (KAP/MKK ADAYLARI)
                    // =========================================================
                    Loader {
                        Layout.fillWidth: true
                        active: root.activeTabIndex === 4
                        visible: root.activeTabIndex === 4
                        source: "../components/SettingsCorporateActionsTab.qml"
                        onLoaded: item.notify.connect(function(success, message) { settingsToast.show(message, success) })
                    }

                    // =========================================================
                    // SEKME 5: FİYAT VERİSİ YÖNETİMİ
                    // =========================================================
                    Loader {
                        Layout.fillWidth: true
                        active: root.activeTabIndex === 5
                        visible: root.activeTabIndex === 5
                        source: "../components/SettingsPriceDataTab.qml"
                        onLoaded: item.notify.connect(function(success, message) { settingsToast.show(message, success) })
                    }

                    // =========================================================
                    // SEKME 6: PİYASA DÜZELTMELERİ (TÜM BIST SERMAYE ARTIRIMI)
                    // =========================================================
                    Loader {
                        Layout.fillWidth: true
                        active: root.activeTabIndex === 6
                        visible: root.activeTabIndex === 6
                        source: "../components/SettingsMarketAdjustmentsTab.qml"
                        onLoaded: item.notify.connect(function(success, message) { settingsToast.show(message, success) })
                    }

                    // =========================================================
                    // SEKME 7: SİSTEM (OTOMATİK FİYAT YENİLEME, SIFIRLAMA)
                    // =========================================================
                    Loader {
                        Layout.fillWidth: true
                        active: root.activeTabIndex === 7
                        visible: root.activeTabIndex === 7
                        source: "../components/SettingsSystemTab.qml"
                        onLoaded: item.notify.connect(function(success, message) { settingsToast.show(message, success) })
                    }
                }
            }
        }
    }

    // Global Toast Bildirimi
    ToastNotification {
        id: settingsToast
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 24
        z: 999
    }
}
