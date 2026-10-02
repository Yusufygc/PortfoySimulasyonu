import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Yapay zeka sohbet geçmişi: oturum listesi, seçip devam etme, silme.
Rectangle {
    id: root

    property bool isOpen: false
    readonly property bool hasController: typeof aiAdvisorController !== "undefined" && aiAdvisorController

    anchors.fill: parent
    color: "#99000000"
    visible: opacity > 0
    opacity: isOpen ? 1.0 : 0.0
    z: 1000

    Behavior on opacity { NumberAnimation { duration: 160 } }

    function open() { isOpen = true }
    function close() { isOpen = false }

    MouseArea {
        anchors.fill: parent
        onClicked: root.close()
    }

    ModernCard {
        anchors.centerIn: parent
        width: Math.min(480, root.width - 32)
        height: Math.min(520, root.height - 48)

        MouseArea { anchors.fill: parent }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Theme.spaceLg
            spacing: Theme.spaceMd

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: Strings.aiHistoryTitle
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontMd
                    font.weight: Font.Bold
                    color: Theme.textPrimary
                    Layout.fillWidth: true
                }
                ModernButton {
                    text: Strings.aiNewChat
                    variant: "primary"
                    onClicked: {
                        if (root.hasController) aiAdvisorController.newChat()
                        root.close()
                    }
                }
                ModernButton {
                    text: Strings.btnClose
                    variant: "secondary"
                    onClicked: root.close()
                }
            }

            ListView {
                id: sessionList
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: Theme.spaceXs
                model: root.hasController ? aiAdvisorController.sessions : []
                ScrollBar.vertical: ModernScrollBar {}

                delegate: Rectangle {
                    readonly property bool isActive: root.hasController && modelData.id === aiAdvisorController.activeSessionId
                    width: sessionList.width
                    height: 54
                    radius: Theme.radiusSm
                    color: isActive ? Theme.accentSoft : (rowMouse.containsMouse ? Theme.bgCardHover : Theme.bgSecondary)
                    border.color: isActive ? Theme.accent : Theme.borderSubtle
                    border.width: 1

                    MouseArea {
                        id: rowMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            aiAdvisorController.selectSession(modelData.id)
                            root.close()
                        }
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.spaceSm
                        anchors.rightMargin: Theme.spaceSm
                        spacing: Theme.spaceSm

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Text {
                                text: modelData.title
                                color: Theme.textPrimary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSm
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                            Text {
                                text: modelData.updatedText + "  •  " + modelData.messageCount + " " + Strings.aiHistoryQuestions
                                color: Theme.textMuted
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                            }
                        }

                        Rectangle {
                            Layout.preferredWidth: 26
                            Layout.preferredHeight: 26
                            radius: Theme.radiusXs
                            color: delMouse.containsMouse ? Theme.bearRedSoft : "transparent"
                            ModernIcon {
                                anchors.centerIn: parent
                                iconSource: Icons.trash
                                size: 13
                                color: delMouse.containsMouse ? Theme.bearRed : Theme.textMuted
                            }
                            MouseArea {
                                id: delMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: aiAdvisorController.deleteSession(modelData.id)
                            }
                        }
                    }
                }

                Text {
                    anchors.centerIn: parent
                    visible: sessionList.count === 0
                    text: Strings.aiHistoryEmpty
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                }
            }
        }
    }
}
