import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"
import "../components"

Rectangle {
    id: root
    color: "transparent"

    property int activeTabIndex: 0

    // Toast ve Bildirim Yönetimi
    property string toastMessage: ""
    property bool toastSuccess: true
    property bool toastVisible: false

    Connections {
        target: (typeof settingsController !== "undefined") ? settingsController : null
        function onOperationNotification(success, message) {
            root.toastMessage = message
            root.toastSuccess = success
            root.toastVisible = true
            toastTimer.restart()
        }
    }

    Timer {
        id: toastTimer
        interval: 3500
        onTriggered: root.toastVisible = false
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spaceMd

        // ---------------------------------------------------------------------
        // 1. ÜST BAŞLIK & SEKME SEÇİCİ BARI
        // ---------------------------------------------------------------------
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceMd

            ColumnLayout {
                Layout.fillWidth: true
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

            // Sekme Butonları (4 Sekme)
            Rectangle {
                Layout.preferredHeight: 38
                Layout.preferredWidth: rowTabs.implicitWidth + 8
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
                            { name: Strings.settingsTabExport, icon: Icons.fileText }
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
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 16
                        visible: root.activeTabIndex === 0

                        Text {
                            text: "UYGULAMA TEMASI & GÖRÜNÜM"
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            font.weight: Font.Bold
                            font.letterSpacing: 0.5
                        }

                        Text {
                            text: Strings.settingsThemeDesc
                            color: Theme.textSecondary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                        }

                        // Tema Kartları (Koyu vs Açık)
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spaceMd

                            // Koyu Tema Kartı
                            Rectangle {
                                Layout.preferredWidth: 320
                                Layout.preferredHeight: 140
                                radius: Theme.radiusMd
                                color: (typeof settingsController !== "undefined" && settingsController.isDarkTheme)
                                       ? Qt.rgba(0.16, 0.38, 1.0, 0.12)
                                       : Theme.bgSecondary
                                border.color: (typeof settingsController !== "undefined" && settingsController.isDarkTheme)
                                              ? Theme.primary
                                              : Theme.borderSubtle
                                border.width: (typeof settingsController !== "undefined" && settingsController.isDarkTheme) ? 2 : 1

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 16
                                    spacing: 10

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 10

                                        Rectangle {
                                            width: 36
                                            height: 36
                                            radius: 18
                                            color: Theme.bgPrimary

                                            ModernIcon {
                                                anchors.centerIn: parent
                                                iconSource: Icons.moon
                                                size: 18
                                                color: Theme.primary
                                            }
                                        }

                                        ColumnLayout {
                                            spacing: 2
                                            Text {
                                                text: Strings.settingsDarkTheme
                                                color: Theme.textPrimary
                                                font.family: Theme.fontFamily
                                                font.pixelSize: Theme.fontBase
                                                font.weight: Font.Bold
                                            }
                                            Text {
                                                text: "Varsayılan profesyonel koyu tema"
                                                color: Theme.textMuted
                                                font.family: Theme.fontFamily
                                                font.pixelSize: Theme.fontXs
                                            }
                                        }
                                    }

                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 34
                                        radius: Theme.radiusSm
                                        color: (typeof settingsController !== "undefined" && settingsController.isDarkTheme)
                                               ? Theme.primary
                                               : Theme.bgCardHover

                                        Text {
                                            anchors.centerIn: parent
                                            text: (typeof settingsController !== "undefined" && settingsController.isDarkTheme)
                                                  ? "Aktif Tema"
                                                  : "Koyu Temaya Geç"
                                            color: (typeof settingsController !== "undefined" && settingsController.isDarkTheme)
                                                   ? "#FFFFFF"
                                                   : Theme.textSecondary
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.fontXs
                                            font.weight: Font.DemiBold
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                if (typeof settingsController !== "undefined" && !settingsController.isDarkTheme) {
                                                    settingsController.toggleTheme()
                                                    Theme.isDark = settingsController.isDarkTheme
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            // Açık Tema Kartı
                            Rectangle {
                                Layout.preferredWidth: 320
                                Layout.preferredHeight: 140
                                radius: Theme.radiusMd
                                color: (typeof settingsController !== "undefined" && !settingsController.isDarkTheme)
                                       ? Qt.rgba(0.16, 0.38, 1.0, 0.12)
                                       : Theme.bgSecondary
                                border.color: (typeof settingsController !== "undefined" && !settingsController.isDarkTheme)
                                              ? Theme.primary
                                              : Theme.borderSubtle
                                border.width: (typeof settingsController !== "undefined" && !settingsController.isDarkTheme) ? 2 : 1

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 16
                                    spacing: 10

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 10

                                        Rectangle {
                                            width: 36
                                            height: 36
                                            radius: 18
                                            color: Theme.bgPrimary
                                            border.color: Theme.borderSubtle
                                            border.width: 1

                                            ModernIcon {
                                                anchors.centerIn: parent
                                                iconSource: Icons.sun
                                                size: 18
                                                color: Theme.warningYellow
                                            }
                                        }

                                        ColumnLayout {
                                            spacing: 2
                                            Text {
                                                text: Strings.settingsLightTheme
                                                color: Theme.textPrimary
                                                font.family: Theme.fontFamily
                                                font.pixelSize: Theme.fontBase
                                                font.weight: Font.Bold
                                            }
                                            Text {
                                                text: "Ferah ve aydınlık tasarım"
                                                color: Theme.textMuted
                                                font.family: Theme.fontFamily
                                                font.pixelSize: Theme.fontXs
                                            }
                                        }
                                    }

                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 34
                                        radius: Theme.radiusSm
                                        color: (typeof settingsController !== "undefined" && !settingsController.isDarkTheme)
                                               ? Theme.primary
                                               : Theme.bgCardHover

                                        Text {
                                            anchors.centerIn: parent
                                            text: (typeof settingsController !== "undefined" && !settingsController.isDarkTheme)
                                                  ? "Aktif Tema"
                                                  : "Açık Temaya Geç"
                                            color: (typeof settingsController !== "undefined" && !settingsController.isDarkTheme)
                                                   ? "#FFFFFF"
                                                   : Theme.textSecondary
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.fontXs
                                            font.weight: Font.DemiBold
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                if (typeof settingsController !== "undefined" && settingsController.isDarkTheme) {
                                                    settingsController.toggleTheme()
                                                    Theme.isDark = settingsController.isDarkTheme
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            Item { Layout.fillWidth: true }
                        }
                    }

                    // =========================================================
                    // SEKME 1: API ANAHTARLARI & ENTEGRASYONLAR
                    // =========================================================
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 16
                        visible: root.activeTabIndex === 1

                        Text {
                            text: "HARİCİ SERVİS & API YAPILANDIRMASI"
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            font.weight: Font.Bold
                            font.letterSpacing: 0.5
                        }

                        // 1. Google Gemini API Kartı
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 185
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
                                        text: Strings.settingsGeminiKeyTitle
                                        color: Theme.textPrimary
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontBase
                                        font.weight: Font.Bold
                                        Layout.fillWidth: true
                                    }
                                    Text {
                                        text: "Model: Gemini 2.5 Flash"
                                        color: Theme.primary
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontXs
                                        font.weight: Font.DemiBold
                                    }
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: Strings.settingsGeminiKeyDesc
                                    color: Theme.textSecondary
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8

                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 38
                                        radius: Theme.radiusSm
                                        color: Theme.bgInput
                                        border.color: inputGeminiKey.activeFocus ? Theme.primary : Theme.borderSubtle
                                        border.width: 1

                                        TextInput {
                                            id: inputGeminiKey
                                            anchors.fill: parent
                                            anchors.margins: 8
                                            color: Theme.textPrimary
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.fontSm
                                            echoMode: btnToggleMask.showKey ? TextInput.Normal : TextInput.Password
                                            text: (typeof settingsController !== "undefined") ? settingsController.geminiApiKey : ""
                                            clip: true
                                        }
                                    }

                                    // Göster/Gizle Butonu
                                    Rectangle {
                                        id: btnToggleMask
                                        property bool showKey: false
                                        Layout.preferredWidth: 38
                                        Layout.preferredHeight: 38
                                        radius: Theme.radiusSm
                                        color: Theme.bgCardHover
                                        border.color: Theme.borderSubtle
                                        border.width: 1

                                        ModernIcon {
                                            anchors.centerIn: parent
                                            iconSource: btnToggleMask.showKey ? Icons.sun : Icons.moon
                                            size: 14
                                            color: Theme.textSecondary
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: btnToggleMask.showKey = !btnToggleMask.showKey
                                        }
                                    }

                                    // Bağlantıyı Test Et Butonu
                                    Rectangle {
                                        Layout.preferredWidth: 160
                                        Layout.preferredHeight: 38
                                        radius: Theme.radiusSm
                                        color: Theme.bgCardHover
                                        border.color: Theme.borderSubtle
                                        border.width: 1

                                        RowLayout {
                                            anchors.centerIn: parent
                                            spacing: 6

                                            ModernIcon {
                                                iconSource: Icons.zap
                                                size: 14
                                                color: Theme.primary
                                            }

                                            Text {
                                                text: Strings.settingsBtnTestConnection
                                                color: Theme.textPrimary
                                                font.family: Theme.fontFamily
                                                font.pixelSize: Theme.fontXs
                                                font.weight: Font.Medium
                                            }
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                if (typeof settingsController !== "undefined") {
                                                    settingsController.testGeminiApiKey(inputGeminiKey.text)
                                                }
                                            }
                                        }
                                    }
                                }

                                // Test Sonuç Rozeti
                                Text {
                                    visible: (typeof settingsController !== "undefined") && settingsController.apiTestResult.length > 0
                                    text: (typeof settingsController !== "undefined") ? settingsController.apiTestResult : ""
                                    color: (typeof settingsController !== "undefined" && settingsController.apiTestResult.indexOf("Başarılı") !== -1)
                                           ? Theme.bullGreen
                                           : Theme.bearRed
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                    font.weight: Font.Medium
                                }
                            }
                        }

                        // 2. TCMB EVDS API Kartı
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 145
                            radius: Theme.radiusMd
                            color: Theme.bgSecondary
                            border.color: Theme.borderSubtle
                            border.width: 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 16
                                spacing: 10

                                Text {
                                    text: Strings.settingsEvdsKeyTitle
                                    color: Theme.textPrimary
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontBase
                                    font.weight: Font.Bold
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: Strings.settingsEvdsKeyDesc
                                    color: Theme.textSecondary
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 38
                                    radius: Theme.radiusSm
                                    color: Theme.bgInput
                                    border.color: inputEvdsKey.activeFocus ? Theme.primary : Theme.borderSubtle
                                    border.width: 1

                                    TextInput {
                                        id: inputEvdsKey
                                        anchors.fill: parent
                                        anchors.margins: 8
                                        color: Theme.textPrimary
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSm
                                        echoMode: TextInput.Password
                                        text: (typeof settingsController !== "undefined") ? settingsController.evdsApiKey : ""
                                        clip: true
                                    }
                                }
                            }
                        }

                        // Kaydet Butonu
                        Rectangle {
                            Layout.preferredWidth: 220
                            Layout.preferredHeight: 38
                            radius: Theme.radiusSm
                            color: btnSaveKeyMouse.containsMouse ? Theme.primaryHover : Theme.primary

                            RowLayout {
                                anchors.centerIn: parent
                                spacing: 8

                                ModernIcon {
                                    iconSource: Icons.check
                                    size: 14
                                    color: "#FFFFFF"
                                }

                                Text {
                                    text: "API Anahtarlarını Kaydet"
                                    color: "#FFFFFF"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSm
                                    font.weight: Font.DemiBold
                                }
                            }

                            MouseArea {
                                id: btnSaveKeyMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    if (typeof settingsController !== "undefined") {
                                        settingsController.saveApiKeys(inputGeminiKey.text, inputEvdsKey.text)
                                    }
                                }
                            }
                        }
                    }

                    // =========================================================
                    // SEKME 2: VERİ SAĞLIĞI & SENKRONİZASYON (ÇİFT MOTOR)
                    // =========================================================
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 16
                        visible: root.activeTabIndex === 2

                        Text {
                            text: "ÇİFT MOTORLU HİBRİT VERİTABANI İSTATİSTİKLERİ"
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
                                                    text: modelData.count + " kayıt"
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

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 8

                                        RowLayout {
                                            Layout.fillWidth: true
                                            Text { text: "Kapsanan BIST Hissesi:"; color: Theme.textSecondary; font.pixelSize: Theme.fontXs; Layout.fillWidth: true }
                                            Text { text: (typeof settingsController !== "undefined") ? settingsController.duckDbStockCount + " Hisse" : "624 Hisse"; color: Theme.textPrimary; font.weight: Font.DemiBold; font.pixelSize: Theme.fontXs }
                                        }

                                        RowLayout {
                                            Layout.fillWidth: true
                                            Text { text: "Toplam Tarihsel Günlük Bar:"; color: Theme.textSecondary; font.pixelSize: Theme.fontXs; Layout.fillWidth: true }
                                            Text { text: (typeof settingsController !== "undefined") ? settingsController.duckDbTotalBars + " Bar" : "0 Bar"; color: Theme.textPrimary; font.weight: Font.DemiBold; font.pixelSize: Theme.fontXs }
                                        }

                                        RowLayout {
                                            Layout.fillWidth: true
                                            Text { text: "Son Senkronizasyon Tarihi:"; color: Theme.textSecondary; font.pixelSize: Theme.fontXs; Layout.fillWidth: true }
                                            Text { text: (typeof settingsController !== "undefined") ? settingsController.duckDbLastDate : "-"; color: Theme.bullGreen; font.weight: Font.Bold; font.pixelSize: Theme.fontXs }
                                        }

                                        RowLayout {
                                            Layout.fillWidth: true
                                            Text { text: "Otomatik Senkronizasyon:"; color: Theme.textSecondary; font.pixelSize: Theme.fontXs; Layout.fillWidth: true }
                                            Text { text: "Her İşlem Günü 18:15"; color: Theme.primary; font.weight: Font.DemiBold; font.pixelSize: Theme.fontXs }
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

                    // =========================================================
                    // SEKME 3: DIŞA AKTARIM & YEDEKLEME (EXPORT / BACKUP)
                    // =========================================================
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 16
                        visible: root.activeTabIndex === 3

                        Text {
                            text: "PORTFÖY VERİLERİNİ DIŞA AKTAR VE YEDEKLE"
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            font.weight: Font.Bold
                            font.letterSpacing: 0.5
                        }

                        // Excel Export Kartı
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 120
                            radius: Theme.radiusMd
                            color: Theme.bgSecondary
                            border.color: Theme.borderSubtle
                            border.width: 1

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 16
                                spacing: 16

                                Rectangle {
                                    Layout.preferredWidth: 48
                                    Layout.preferredHeight: 48
                                    radius: 24
                                    color: Qt.rgba(0.06, 0.72, 0.51, 0.15)

                                    ModernIcon {
                                        anchors.centerIn: parent
                                        iconSource: Icons.fileText
                                        size: 24
                                        color: Theme.bullGreen
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4

                                    Text {
                                        text: Strings.settingsExportExcel
                                        color: Theme.textPrimary
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontBase
                                        font.weight: Font.Bold
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: Strings.settingsExportExcelDesc
                                        color: Theme.textSecondary
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontXs
                                        wrapMode: Text.Wrap
                                    }
                                }

                                Rectangle {
                                    Layout.preferredWidth: 160
                                    Layout.preferredHeight: 38
                                    radius: Theme.radiusSm
                                    color: btnExcelMouse.containsMouse ? Theme.bullGreenSoft : Theme.bullGreen

                                    Text {
                                        anchors.centerIn: parent
                                        text: "Excel İndir (.xlsx)"
                                        color: "#FFFFFF"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontXs
                                        font.weight: Font.DemiBold
                                    }

                                    MouseArea {
                                        id: btnExcelMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            if (typeof settingsController !== "undefined") {
                                                settingsController.exportPortfolioToExcel()
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        // JSON Export Kartı
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 120
                            radius: Theme.radiusMd
                            color: Theme.bgSecondary
                            border.color: Theme.borderSubtle
                            border.width: 1

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 16
                                spacing: 16

                                Rectangle {
                                    Layout.preferredWidth: 48
                                    Layout.preferredHeight: 48
                                    radius: 24
                                    color: Qt.rgba(0.16, 0.38, 1.0, 0.15)

                                    ModernIcon {
                                        anchors.centerIn: parent
                                        iconSource: Icons.settings
                                        size: 24
                                        color: Theme.primary
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4

                                    Text {
                                        text: Strings.settingsExportJson
                                        color: Theme.textPrimary
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontBase
                                        font.weight: Font.Bold
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: Strings.settingsExportJsonDesc
                                        color: Theme.textSecondary
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontXs
                                        wrapMode: Text.Wrap
                                    }
                                }

                                Rectangle {
                                    Layout.preferredWidth: 160
                                    Layout.preferredHeight: 38
                                    radius: Theme.radiusSm
                                    color: btnJsonMouse.containsMouse ? Theme.primaryHover : Theme.primary

                                    Text {
                                        anchors.centerIn: parent
                                        text: "JSON Yedeği Al"
                                        color: "#FFFFFF"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontXs
                                        font.weight: Font.DemiBold
                                    }

                                    MouseArea {
                                        id: btnJsonMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            if (typeof settingsController !== "undefined") {
                                                settingsController.exportPortfolioToJson()
                                            }
                                        }
                                    }
                                }
                            }
                        }
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
        visible: root.toastVisible
    }
}
