import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Yapay zeka sayfası sohbet terminali: hızlı sorular, mesaj listesi ve giriş alanı.
Rectangle {
    id: root
    // Yeni mesaj geldiğinde listeyi en sona kaydırır
    function scrollToEnd() {
        if (chatListView.count > 0) {
            chatListView.positionViewAtEnd()
        }
    }
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
