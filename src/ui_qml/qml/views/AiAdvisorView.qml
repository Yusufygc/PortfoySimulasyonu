import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"
import "../components"

Rectangle {
    id: root
    color: "transparent"

    // Toast ve Bildirim Yönetimi
    property string toastMessage: ""
    property bool toastSuccess: true
    property bool toastVisible: false

    Connections {
        target: (typeof aiAdvisorController !== "undefined") ? aiAdvisorController : null
        function onAiErrorOccurred(errorMsg) {
            root.toastMessage = errorMsg
            root.toastSuccess = false
            root.toastVisible = true
            toastTimer.restart()
        }
        function onMessageReceived(role, content) {
            // Yeni mesaj geldiğinde listeyi en sona kaydır
            Qt.callLater(function() {
                if (chatListView.count > 0) {
                    chatListView.positionViewAtEnd()
                }
            })
        }
    }

    Timer {
        id: toastTimer
        interval: 3500
        onTriggered: root.toastVisible = false
    }

    // Sayfa modu: 0 = Portföy Danışmanı (sohbet), 1 = Hisse Modeli (AI_Core model analizi)
    property int mode: 0

    // Dar pencerede sağlık paneli sohbetin altına iner (ana sayfa kaydırması devreye girer)
    readonly property bool stacked: width < 940
    readonly property int minContentHeight: mode === 0 ? (stacked ? 1080 : 0) : 900

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spaceMd

        // ---------------------------------------------------------------------
        // 1. ÜST BAŞLIK & DURUM BARI
        // ---------------------------------------------------------------------
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceMd

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                Text {
                    text: Strings.aiAdvisorTitle
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXl
                    font.weight: Font.Bold
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }

                Text {
                    text: Strings.aiAdvisorSubtitle
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }

            // Model ve Durum Rozeti
            Rectangle {
                Layout.preferredHeight: 36
                Layout.preferredWidth: rowStatus.implicitWidth + 24
                radius: Theme.radiusMd
                color: Theme.bgSurface
                border.color: (typeof aiAdvisorController !== "undefined" && aiAdvisorController.hasApiKey)
                              ? Theme.primary
                              : Theme.borderSubtle
                border.width: 1

                RowLayout {
                    id: rowStatus
                    anchors.centerIn: parent
                    spacing: Theme.spaceXs

                    // Durum Işığı
                    Rectangle {
                        width: 8
                        height: 8
                        radius: 4
                        color: (typeof aiAdvisorController !== "undefined" && aiAdvisorController.isLoading)
                               ? Theme.accentWarning
                               : (typeof aiAdvisorController !== "undefined" && aiAdvisorController.hasApiKey)
                                 ? Theme.bullGreen
                                 : Theme.primary

                        SequentialAnimation on opacity {
                            running: (typeof aiAdvisorController !== "undefined" && aiAdvisorController.isLoading)
                            loops: Animation.Infinite
                            PropertyAnimation { to: 0.3; duration: 600 }
                            PropertyAnimation { to: 1.0; duration: 600 }
                        }
                    }

                    Text {
                        text: (typeof aiAdvisorController !== "undefined") ? aiAdvisorController.modelName : "Gemini 2.5 Flash"
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        font.weight: Font.DemiBold
                    }

                    Text {
                        text: (typeof aiAdvisorController !== "undefined" && aiAdvisorController.hasApiKey)
                              ? Strings.aiBadgeOnline
                              : Strings.aiBadgeSimulation
                        color: (typeof aiAdvisorController !== "undefined" && aiAdvisorController.hasApiKey)
                               ? Theme.bullGreen
                               : Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                    }
                }
            }

            // Sohbet Geçmişi Butonu
            Rectangle {
                visible: typeof aiAdvisorController !== "undefined" && aiAdvisorController.historyAvailable
                Layout.preferredHeight: 36
                Layout.preferredWidth: rowHistory.implicitWidth + 20
                radius: Theme.radiusMd
                color: btnHistoryMouse.containsMouse ? Theme.bgSurfaceHover : Theme.bgSurface
                border.color: Theme.borderSubtle
                border.width: 1

                RowLayout {
                    id: rowHistory
                    anchors.centerIn: parent
                    spacing: Theme.spaceXs

                    ModernIcon {
                        iconSource: Icons.history
                        size: 14
                        color: Theme.textSecondary
                    }

                    Text {
                        text: Strings.aiHistory
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        font.weight: Font.Medium
                    }
                }

                MouseArea {
                    id: btnHistoryMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: chatHistoryDialog.open()
                }
            }

            // Yeni Sohbet Butonu (eski ad: Sohbeti Temizle; geçmiş korunur)
            Rectangle {
                Layout.preferredHeight: 36
                Layout.preferredWidth: rowClear.implicitWidth + 20
                radius: Theme.radiusMd
                color: btnClearMouse.containsMouse ? Theme.bgSurfaceHover : Theme.bgSurface
                border.color: Theme.borderSubtle
                border.width: 1

                RowLayout {
                    id: rowClear
                    anchors.centerIn: parent
                    spacing: Theme.spaceXs

                    ModernIcon {
                        iconSource: Icons.trash
                        size: 14
                        color: Theme.textSecondary
                    }

                    Text {
                        text: Strings.aiClearChat
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        font.weight: Font.Medium
                    }
                }

                MouseArea {
                    id: btnClearMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (typeof aiAdvisorController !== "undefined") {
                            aiAdvisorController.clearChat()
                        }
                    }
                }
            }
        }

        // Mod anahtarı
        Flow {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            ModernButton {
                text: Strings.aiModeAdvisor
                variant: root.mode === 0 ? "primary" : "secondary"
                onClicked: root.mode = 0
            }
            ModernButton {
                text: Strings.aiModeModel
                variant: root.mode === 1 ? "primary" : "secondary"
                onClicked: root.mode = 1
            }
        }

        ModelAnalysisPanel {
            visible: root.mode === 1
            Layout.fillWidth: true
            Layout.fillHeight: true
            onSendToAdvisorRequested: function(prompt) {
                root.mode = 0
                if (typeof aiAdvisorController !== "undefined") aiAdvisorController.sendMessage(prompt)
            }
        }

        // ---------------------------------------------------------------------
        // 2. ANA GÖVDE: SOL SOHBET TERMİNALİ (%68) + SAĞ SAĞLIK PANELİ (%32)
        // ---------------------------------------------------------------------
        GridLayout {
            visible: root.mode === 0
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: root.stacked ? 1 : 2
            columnSpacing: Theme.spaceMd
            rowSpacing: Theme.spaceMd

            // =================================================================
            // SOL ALAN: SOHBET TERMİNALİ
            // =================================================================
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredHeight: 520
                radius: Theme.radiusMd
                color: Theme.bgCard
                border.color: Theme.borderCard
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spaceMd
                    spacing: Theme.spaceSm

                    // A) Hızlı Soru Önerileri Çipleri
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 6

                        Text {
                            text: Strings.aiQuickPromptsTitle
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            font.weight: Font.Bold
                            font.letterSpacing: 0.5
                        }

                        Flickable {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 38
                            contentWidth: quickRow.implicitWidth
                            contentHeight: 38
                            clip: true
                            flickableDirection: Flickable.HorizontalFlick
                            boundsBehavior: Flickable.StopAtBounds

                            RowLayout {
                                id: quickRow
                                spacing: 8

                                Repeater {
                                    model: (typeof aiAdvisorController !== "undefined") ? aiAdvisorController.quickPrompts : []

                                    Rectangle {
                                        Layout.preferredHeight: 34
                                        Layout.preferredWidth: rowChip.implicitWidth + 24
                                        radius: 17
                                        color: chipMouse.containsMouse ? Theme.bgSurfaceHover : Theme.bgSurface
                                        border.color: chipMouse.containsMouse ? Theme.primary : Theme.borderSubtle
                                        border.width: 1

                                        RowLayout {
                                            id: rowChip
                                            anchors.centerIn: parent
                                            spacing: 6

                                            ModernIcon {
                                                iconSource: Icons.get(modelData.icon)
                                                size: 14
                                                color: chipMouse.containsMouse ? Theme.primary : Theme.textSecondary
                                            }

                                            Text {
                                                text: modelData.title
                                                color: chipMouse.containsMouse ? Theme.textPrimary : Theme.textSecondary
                                                font.family: Theme.fontFamily
                                                font.pixelSize: Theme.fontXs
                                                font.weight: Font.Medium
                                            }
                                        }

                                        MouseArea {
                                            id: chipMouse
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            enabled: (typeof aiAdvisorController !== "undefined") && !aiAdvisorController.isLoading
                                            onClicked: {
                                                if (typeof aiAdvisorController !== "undefined") {
                                                    aiAdvisorController.sendQuickPrompt(index)
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.borderSubtle
                    }

                    // B) Mesaj Akışı (ListView)
                    ListView {
                        id: chatListView
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 14
                        model: (typeof aiAdvisorController !== "undefined") ? aiAdvisorController.messages : []
                        ScrollBar.vertical: ModernScrollBar {}

                        onCountChanged: {
                            Qt.callLater(function() {
                                chatListView.positionViewAtEnd()
                            })
                        }

                        delegate: Item {
                            width: chatListView.width
                            height: colMsg.implicitHeight

                            ColumnLayout {
                                id: colMsg
                                width: parent.width
                                spacing: 4

                                // Kullanıcı Mesajı (Sağa Yaslı)
                                RowLayout {
                                    visible: modelData.role === "user"
                                    Layout.fillWidth: true
                                    Layout.alignment: Qt.AlignRight

                                    Item { Layout.fillWidth: true } // Boşluk

                                    Rectangle {
                                        Layout.maximumWidth: Math.min(chatListView.width * 0.78, 620)
                                        Layout.preferredWidth: txtUser.implicitWidth + 28
                                        Layout.preferredHeight: txtUser.implicitHeight + 20
                                        radius: Theme.radiusMd
                                        color: Theme.primary

                                        Text {
                                            id: txtUser
                                            anchors.fill: parent
                                            anchors.margins: 10
                                            text: modelData.content
                                            color: "#FFFFFF"
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.fontSm
                                            wrapMode: Text.Wrap
                                        }
                                    }
                                }

                                // AI Mesajı (Sola Yaslı)
                                RowLayout {
                                    visible: modelData.role === "ai"
                                    Layout.fillWidth: true
                                    Layout.alignment: Qt.AlignLeft
                                    spacing: 10

                                    // AI Avatar Rozeti
                                    Rectangle {
                                        Layout.preferredWidth: 32
                                        Layout.preferredHeight: 32
                                        Layout.alignment: Qt.AlignTop
                                        radius: 16
                                        color: Theme.bgSurface
                                        border.color: Theme.primary
                                        border.width: 1

                                        ModernIcon {
                                            anchors.centerIn: parent
                                            iconSource: Icons.ai
                                            size: 16
                                            color: Theme.primary
                                        }
                                    }

                                    // AI Mesaj Kartı
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.maximumWidth: Math.min(chatListView.width * 0.88, 720)
                                        Layout.preferredHeight: colAiContent.implicitHeight + 24
                                        radius: Theme.radiusMd
                                        color: Theme.bgSurface
                                        border.color: Theme.borderSubtle
                                        border.width: 1

                                        ColumnLayout {
                                            id: colAiContent
                                            anchors.fill: parent
                                            anchors.margins: 12
                                            spacing: 10

                                            // Zengin Markdown / Metin Alanı
                                            TextEdit {
                                                Layout.fillWidth: true
                                                text: modelData.content
                                                color: Theme.textPrimary
                                                font.family: Theme.fontFamily
                                                font.pixelSize: Theme.fontSm
                                                wrapMode: TextEdit.Wrap
                                                readOnly: true
                                                selectByMouse: true
                                                textFormat: TextEdit.MarkdownText
                                                selectedTextColor: "#FFFFFF"
                                                selectionColor: Theme.primary
                                            }

                                            // Kullanılan Analiz Araçları (Function Calling Rozetleri)
                                            Flow {
                                                Layout.fillWidth: true
                                                spacing: 6
                                                visible: modelData.toolCalls && modelData.toolCalls.length > 0

                                                Repeater {
                                                    model: modelData.toolCalls || []

                                                    Rectangle {
                                                        height: 22
                                                        width: rowTool.implicitWidth + 14
                                                        radius: 11
                                                        color: Theme.bgCard
                                                        border.color: Theme.bullGreen
                                                        border.width: 1

                                                        RowLayout {
                                                            id: rowTool
                                                            anchors.centerIn: parent
                                                            spacing: 4

                                                            ModernIcon {
                                                                iconSource: Icons.check
                                                                size: 10
                                                                color: Theme.bullGreen
                                                            }

                                                            Text {
                                                                text: modelData.label || modelData.name
                                                                color: Theme.textSecondary
                                                                font.family: Theme.fontFamily
                                                                font.pixelSize: 10
                                                                font.weight: Font.Medium
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }

                                // Sistem / Bilgi Mesajı (Ortalanmış)
                                RowLayout {
                                    visible: modelData.role === "system"
                                    Layout.fillWidth: true
                                    Layout.alignment: Qt.AlignHCenter

                                    Rectangle {
                                        Layout.preferredWidth: txtSys.implicitWidth + 30
                                        Layout.preferredHeight: txtSys.implicitHeight + 14
                                        radius: Theme.radiusSm
                                        color: Theme.bgSurface
                                        border.color: Theme.borderSubtle
                                        border.width: 1

                                        Text {
                                            id: txtSys
                                            anchors.centerIn: parent
                                            text: modelData.content
                                            color: Theme.textMuted
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.fontXs
                                            wrapMode: Text.Wrap
                                        }
                                    }
                                }

                                // Zaman Damgası
                                Text {
                                    text: modelData.timestamp || ""
                                    color: Theme.textMuted
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 10
                                    Layout.alignment: (modelData.role === "user") ? Qt.AlignRight : Qt.AlignLeft
                                    Layout.leftMargin: (modelData.role === "ai") ? 42 : 0
                                    Layout.rightMargin: (modelData.role === "user") ? 4 : 0
                                }
                            }
                        }
                    }

                    // C) AI Düşünüyor / Yükleniyor Göstergesi
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        visible: (typeof aiAdvisorController !== "undefined") && aiAdvisorController.isLoading

                        Rectangle {
                            width: 24
                            height: 24
                            radius: 12
                            color: Theme.bgSurface
                            border.color: Theme.primary
                            border.width: 1

                            ModernIcon {
                                anchors.centerIn: parent
                                iconSource: Icons.ai
                                size: 12
                                color: Theme.primary
                            }
                        }

                        Text {
                            text: Strings.aiStatusThinking
                            color: Theme.textSecondary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            font.italic: true
                        }
                    }

                    // D) Alt Girdi ve Gönderim Alanı
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 52
                        radius: Theme.radiusMd
                        color: Theme.bgSurface
                        border.color: txtInput.activeFocus ? Theme.primary : Theme.borderSubtle
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 14
                            anchors.rightMargin: 8
                            spacing: 8

                            TextInput {
                                id: txtInput
                                Layout.fillWidth: true
                                color: Theme.textPrimary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSm
                                verticalAlignment: TextInput.AlignVCenter
                                clip: true
                                activeFocusOnTab: true
                                maximumLength: (typeof aiAdvisorController !== "undefined") ? aiAdvisorController.maxInputLength : 750

                                Text {
                                    text: Strings.aiInputPlaceholder
                                    color: Theme.textMuted
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSm
                                    visible: !txtInput.text && !txtInput.activeFocus
                                    anchors.left: parent.left
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                onAccepted: {
                                    if (txtInput.text.trim().length > 0 && typeof aiAdvisorController !== "undefined" && !aiAdvisorController.isLoading) {
                                        if (aiAdvisorController.submitUserMessage(txtInput.text)) txtInput.text = ""
                                    }
                                }
                            }

                            // Gönder Butonu
                            Rectangle {
                                Layout.preferredWidth: 38
                                Layout.preferredHeight: 38
                                radius: 19
                                color: (txtInput.text.trim().length > 0 && typeof aiAdvisorController !== "undefined" && !aiAdvisorController.isLoading)
                                       ? (btnSendMouse.containsMouse ? Theme.primaryHover : Theme.primary)
                                       : Theme.bgCard
                                border.color: Theme.borderSubtle
                                border.width: 1

                                ModernIcon {
                                    anchors.centerIn: parent
                                    iconSource: Icons.send
                                    size: 16
                                    color: (txtInput.text.trim().length > 0 && typeof aiAdvisorController !== "undefined" && !aiAdvisorController.isLoading)
                                           ? "#FFFFFF"
                                           : Theme.textMuted
                                }

                                MouseArea {
                                    id: btnSendMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: (txtInput.text.trim().length > 0) ? Qt.PointingHandCursor : Qt.ArrowCursor
                                    onClicked: {
                                        if (txtInput.text.trim().length > 0 && typeof aiAdvisorController !== "undefined" && !aiAdvisorController.isLoading) {
                                            if (aiAdvisorController.submitUserMessage(txtInput.text)) txtInput.text = ""
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // Yasal Uyarı
                    Text {
                        Layout.fillWidth: true
                        text: Strings.aiDisclaimer
                        color: Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: 10
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
            }

            // =================================================================
            // SAĞ ALAN: PORTFÖY SAĞLIK & XAI RİSK PANELİ (%32, 340px)
            // =================================================================
            Rectangle {
                Layout.fillWidth: root.stacked
                Layout.preferredWidth: root.stacked ? -1 : 340
                Layout.preferredHeight: root.stacked ? 460 : -1
                Layout.fillHeight: !root.stacked
                radius: Theme.radiusMd
                color: Theme.bgCard
                border.color: Theme.borderCard
                border.width: 1

                ScrollView {
                    id: rightScroll
                    anchors.fill: parent
                    anchors.margins: Theme.spaceMd
                    clip: true
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                    ScrollBar.vertical: ModernScrollBar {}

                    ColumnLayout {
                        id: colHealth
                        width: rightScroll.availableWidth
                        spacing: 14

                            // Başlık
                            Text {
                                text: Strings.aiHealthScoreTitle
                                color: Theme.textMuted
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                font.weight: Font.Bold
                                font.letterSpacing: 0.5
                            }

                            // Büyük Sağlık Skoru Kartı
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 110
                                radius: Theme.radiusMd
                                color: Theme.bgSurface
                                border.color: Theme.borderSubtle
                                border.width: 1

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    spacing: 14

                                    // Büyük Dairesel Skor
                                    Rectangle {
                                        Layout.preferredWidth: 76
                                        Layout.preferredHeight: 76
                                        radius: 38
                                        color: "transparent"
                                        border.color: {
                                            var score = (typeof aiAdvisorController !== "undefined") ? aiAdvisorController.portfolioHealthScore : 75
                                            if (score >= 80) return Theme.bullGreen
                                            if (score >= 65) return Theme.primary
                                            if (score >= 50) return Theme.accentWarning
                                            return Theme.bearRed
                                        }
                                        border.width: 3

                                        ColumnLayout {
                                            anchors.centerIn: parent
                                            spacing: -2

                                            Text {
                                                text: (typeof aiAdvisorController !== "undefined") ? aiAdvisorController.portfolioHealthScore : "75"
                                                color: Theme.textPrimary
                                                font.family: Theme.fontFamily
                                                font.pixelSize: 26
                                                font.weight: Font.Bold
                                                Layout.alignment: Qt.AlignHCenter
                                            }

                                            Text {
                                                text: "/ 100"
                                                color: Theme.textMuted
                                                font.family: Theme.fontFamily
                                                font.pixelSize: 9
                                                Layout.alignment: Qt.AlignHCenter
                                            }
                                        }
                                    }

                                    // Skor Etiketi & Bilgisi
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 4

                                        Rectangle {
                                            Layout.preferredHeight: 22
                                            Layout.preferredWidth: lblBadge.implicitWidth + 16
                                            radius: 11
                                            color: {
                                                var score = (typeof aiAdvisorController !== "undefined") ? aiAdvisorController.portfolioHealthScore : 75
                                                if (score >= 80) return Qt.rgba(0.06, 0.72, 0.51, 0.15)
                                                if (score >= 65) return Qt.rgba(0.38, 0.40, 0.95, 0.15)
                                                if (score >= 50) return Qt.rgba(0.96, 0.62, 0.18, 0.15)
                                                return Qt.rgba(0.94, 0.27, 0.24, 0.15)
                                            }

                                            Text {
                                                id: lblBadge
                                                anchors.centerIn: parent
                                                text: (typeof aiAdvisorController !== "undefined") ? aiAdvisorController.healthScoreLabel : "Dengeli"
                                                color: {
                                                    var score = (typeof aiAdvisorController !== "undefined") ? aiAdvisorController.portfolioHealthScore : 75
                                                    if (score >= 80) return Theme.bullGreen
                                                    if (score >= 65) return Theme.primary
                                                    if (score >= 50) return Theme.accentWarning
                                                    return Theme.bearRed
                                                }
                                                font.family: Theme.fontFamily
                                                font.pixelSize: 11
                                                font.weight: Font.DemiBold
                                            }
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: Strings.aiHealthScoreDesc
                                            color: Theme.textSecondary
                                            font.family: Theme.fontFamily
                                            font.pixelSize: 11
                                            wrapMode: Text.Wrap
                                        }
                                    }
                                }
                            }

                            // Ayırıcı
                            Rectangle {
                                Layout.fillWidth: true
                                height: 1
                                color: Theme.borderSubtle
                            }

                            // XAI Risk Faktörleri Başlığı
                            RowLayout {
                                Layout.fillWidth: true

                                Text {
                                    text: Strings.aiXaiInsightsTitle
                                    color: Theme.textMuted
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                    font.weight: Font.Bold
                                    font.letterSpacing: 0.5
                                    Layout.fillWidth: true
                                }

                                ModernIcon {
                                    iconSource: Icons.activity
                                    size: 14
                                    color: Theme.textMuted
                                }
                            }

                            // 4 Risk & Sağlık Boyutu Listesi
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 10

                                Repeater {
                                    model: (typeof aiAdvisorController !== "undefined") ? aiAdvisorController.healthFactors : []

                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 64
                                        radius: Theme.radiusSm
                                        color: Theme.bgSurface
                                        border.color: Theme.borderSubtle
                                        border.width: 1

                                        ColumnLayout {
                                            anchors.fill: parent
                                            anchors.margins: 10
                                            spacing: 6

                                            RowLayout {
                                                Layout.fillWidth: true

                                                Text {
                                                    text: modelData.title
                                                    color: Theme.textPrimary
                                                    font.family: Theme.fontFamily
                                                    font.pixelSize: Theme.fontXs
                                                    font.weight: Font.DemiBold
                                                    Layout.fillWidth: true
                                                }

                                                Text {
                                                    text: modelData.value
                                                    color: modelData.isGood ? Theme.bullGreen : Theme.accentWarning
                                                    font.family: Theme.fontFamily
                                                    font.pixelSize: Theme.fontXs
                                                    font.weight: Font.Bold
                                                }
                                            }

                                            // İlerleme Çubuğu
                                            Rectangle {
                                                Layout.fillWidth: true
                                                height: 4
                                                radius: 2
                                                color: Theme.bgCard

                                                Rectangle {
                                                    height: parent.height
                                                    width: parent.width * Math.min(1.0, (modelData.score / (modelData.maxScore || 25)))
                                                    radius: 2
                                                    color: modelData.isGood ? Theme.bullGreen : Theme.accentWarning
                                                }
                                            }

                                            Text {
                                                text: modelData.status
                                                color: Theme.textMuted
                                                font.family: Theme.fontFamily
                                                font.pixelSize: 10
                                            }
                                        }
                                    }
                                }
                            }

                            // Ayırıcı
                            Rectangle {
                                Layout.fillWidth: true
                                height: 1
                                color: Theme.borderSubtle
                            }

                            // API Anahtarı Durumu / Tanımlama Kartı
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: (typeof aiAdvisorController !== "undefined" && aiAdvisorController.hasApiKey) ? 44 : 110
                                radius: Theme.radiusSm
                                color: Theme.bgSurface
                                border.color: (typeof aiAdvisorController !== "undefined" && aiAdvisorController.hasApiKey)
                                              ? Qt.rgba(0.06, 0.72, 0.51, 0.3)
                                              : Qt.rgba(0.96, 0.62, 0.18, 0.3)
                                border.width: 1

                                // Durum 1: API Key Mevcut
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 8
                                    visible: (typeof aiAdvisorController !== "undefined" && aiAdvisorController.hasApiKey)

                                    ModernIcon {
                                        iconSource: Icons.check
                                        size: 16
                                        color: Theme.bullGreen
                                    }

                                    Text {
                                        text: Strings.aiGeminiActive
                                        color: Theme.textPrimary
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontXs
                                        font.weight: Font.Medium
                                        Layout.fillWidth: true
                                    }
                                }

                                // Durum 2: API Key Tanımlanmamış
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 8
                                    visible: (typeof aiAdvisorController !== "undefined" && !aiAdvisorController.hasApiKey)

                                    Text {
                                        Layout.fillWidth: true
                                        text: Strings.aiApiKeyMissingNotice
                                        color: Theme.textSecondary
                                        font.family: Theme.fontFamily
                                        font.pixelSize: 10
                                        wrapMode: Text.Wrap
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 6

                                        Rectangle {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 30
                                            radius: 4
                                            color: Theme.bgCard
                                            border.color: Theme.borderSubtle
                                            border.width: 1

                                            TextInput {
                                                id: txtApiKey
                                                anchors.fill: parent
                                                anchors.margins: 6
                                                color: Theme.textPrimary
                                                font.family: Theme.fontFamily
                                                font.pixelSize: Theme.fontXs
                                                clip: true
                                                echoMode: TextInput.Password

                                                Text {
                                                    text: Strings.aiKeyPlaceholder
                                                    color: Theme.textMuted
                                                    font.family: Theme.fontFamily
                                                    font.pixelSize: 10
                                                    visible: !txtApiKey.text
                                                    anchors.left: parent.left
                                                    anchors.verticalCenter: parent.verticalCenter
                                                }
                                            }
                                        }

                                        Rectangle {
                                            Layout.preferredWidth: 64
                                            Layout.preferredHeight: 30
                                            radius: 4
                                            color: Theme.primary

                                            Text {
                                                anchors.centerIn: parent
                                                text: Strings.btnSave
                                                color: "#FFFFFF"
                                                font.family: Theme.fontFamily
                                                font.pixelSize: Theme.fontXs
                                                font.weight: Font.DemiBold
                                            }

                                            MouseArea {
                                                anchors.fill: parent
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: {
                                                    if (txtApiKey.text.trim().length > 5 && typeof aiAdvisorController !== "undefined") {
                                                        aiAdvisorController.saveApiKey(txtApiKey.text)
                                                        txtApiKey.text = ""
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            // Metrikleri Yenile Butonu
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 34
                                radius: Theme.radiusSm
                                color: btnRefreshMouse.containsMouse ? Theme.bgSurfaceHover : Theme.bgSurface
                                border.color: Theme.borderSubtle
                                border.width: 1

                                RowLayout {
                                    anchors.centerIn: parent
                                    spacing: 6

                                    ModernIcon {
                                        iconSource: Icons.refresh
                                        size: 14
                                        color: Theme.textSecondary
                                    }

                                    Text {
                                        text: Strings.aiRefreshHealthMetrics
                                        color: Theme.textSecondary
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontXs
                                        font.weight: Font.Medium
                                    }
                                }

                                MouseArea {
                                    id: btnRefreshMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (typeof aiAdvisorController !== "undefined") {
                                            aiAdvisorController.refreshHealthScore()
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
        id: advisorToast
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 24
        z: 999
        visible: root.toastVisible
    }

    ChatHistoryDialog {
        id: chatHistoryDialog
    }
}
