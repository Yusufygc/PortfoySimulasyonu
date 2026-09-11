import QtQuick
import QtQuick.Controls

// AiAdvisorView (bkz. plan §6.2, e1.3) — 9. QML görünümü, "AI Danışman".
// GERÇEK Gemini tool-calling sohbeti; mevcut `ai_page` (mock sol panel + gerçek
// düz-sohbet sağ panel) ile HİÇ ilişkili değildir (bkz. plan §6.2.1 kararı).
// Veri: context property `aiAdvisorController` (bkz.
// src/ui_qml/controllers/ai_advisor_controller.py).
//
// Not: Layout `headerColumn` (üstte, otomatik yükseklik) + `inputBar` (altta,
// sabit) + `messagesArea` (Flickable, aradaki kalan alanı dolduran) deseni —
// Stock360View'daki NaN-yükseklik hatasından ders alınarak.
Item {
    id: root
    anchors.fill: parent

    readonly property color colorAccent: "#3B82F6"
    readonly property color colorLoss: "#EF4444"
    readonly property color colorMuted: "#9CA3AF"

    function trySend() {
        if (messageField.text.trim() !== "") {
            aiAdvisorController.sendMessage(messageField.text)
            messageField.text = ""
        }
    }

    Column {
        id: headerColumn
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 20
        spacing: 4

        Text { text: "AI Danışman"; color: "#E5E7EB"; font.pixelSize: 18; font.bold: true }
        Text {
            text: "Gerçek portföy verilerinize erişebilen Gemini asistanı. Bilgilendirme amaçlıdır, yatırım tavsiyesi değildir."
            color: root.colorMuted
            font.pixelSize: 11
            wrapMode: Text.WordWrap
            width: parent.width
        }
    }

    Row {
        id: inputBar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 20
        height: 44
        spacing: 8

        TextField {
            id: messageField
            width: parent.width - sendButton.width - parent.spacing
            height: parent.height
            placeholderText: "Portföyünüz hakkında bir soru sorun..."
            enabled: !aiAdvisorController.isLoading
            onAccepted: root.trySend()
        }

        Button {
            id: sendButton
            height: parent.height
            text: aiAdvisorController.isLoading ? "..." : "Gönder"
            enabled: !aiAdvisorController.isLoading
            onClicked: root.trySend()
        }
    }

    Flickable {
        id: messagesArea
        objectName: "messagesArea"
        anchors.top: headerColumn.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: inputBar.top
        anchors.topMargin: 14
        anchors.leftMargin: 20
        anchors.rightMargin: 20
        anchors.bottomMargin: 10
        contentHeight: messagesColumn.height
        clip: true

        Column {
            id: messagesColumn
            width: messagesArea.width
            spacing: 10

            Text {
                visible: aiAdvisorController.messageTexts.length === 0
                width: parent.width
                text: "Henüz mesaj yok — bir soru sorarak başlayın."
                color: root.colorMuted
                font.pixelSize: 12
            }

            Repeater {
                model: aiAdvisorController.messageTexts.length
                delegate: Item {
                    id: messageRow
                    width: messagesColumn.width
                    height: bubble.height + (toolNamesText.visible ? toolNamesText.height + 2 : 0)

                    property bool isUser: aiAdvisorController.messageRoles[index] === "user"

                    Rectangle {
                        id: bubble
                        width: Math.min(bubbleText.implicitWidth + 24, messageRow.width * 0.75)
                        height: bubbleText.implicitHeight + 16
                        anchors.right: messageRow.isUser ? parent.right : undefined
                        anchors.left: messageRow.isUser ? undefined : parent.left
                        radius: 12
                        color: messageRow.isUser ? root.colorAccent : "#151D2C"
                        border.color: "#26354A"
                        border.width: messageRow.isUser ? 0 : 1

                        Text {
                            id: bubbleText
                            anchors.fill: parent
                            anchors.margins: 8
                            text: aiAdvisorController.messageTexts[index]
                            color: "#E5E7EB"
                            wrapMode: Text.WordWrap
                        }
                    }

                    Text {
                        id: toolNamesText
                        visible: aiAdvisorController.messageToolNames[index] !== ""
                        anchors.top: bubble.bottom
                        anchors.right: messageRow.isUser ? bubble.right : undefined
                        anchors.left: messageRow.isUser ? undefined : bubble.left
                        text: "🔧 " + aiAdvisorController.messageToolNames[index]
                        color: root.colorMuted
                        font.pixelSize: 9
                    }
                }
            }

            Text {
                visible: aiAdvisorController.isLoading
                width: parent.width
                text: "Düşünüyor..."
                color: root.colorMuted
                font.pixelSize: 11
            }

            Text {
                visible: aiAdvisorController.errorMessage !== ""
                width: parent.width
                text: aiAdvisorController.errorMessage
                color: root.colorLoss
                wrapMode: Text.WordWrap
                font.pixelSize: 11
            }
        }
    }
}
