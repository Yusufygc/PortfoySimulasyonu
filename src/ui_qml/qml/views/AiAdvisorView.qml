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
            Qt.callLater(function() { chatTerminal.scrollToEnd() })
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
        AiAdvisorHeader {
            Layout.fillWidth: true
            onHistoryRequested: chatHistoryDialog.open()
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
            AiChatTerminal {
                id: chatTerminal
            }

            // =================================================================
            // SAĞ ALAN: PORTFÖY SAĞLIK & XAI RİSK PANELİ (%32, 340px)
            // =================================================================
            AiHealthPanel {
                stacked: root.stacked
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
