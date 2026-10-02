import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    id: root

    property int activeTabIndex: 0

    // Toast Durumu
    property string toastMessage: ""
    property bool toastSuccess: true
    property bool toastVisible: false

    Connections {
        target: planningController
        function onOperationResult(success, message) {
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

    // Dar pencerede bütçe kalemleri alt alta geçer (ana sayfa kaydırması devreye girer)
    readonly property bool stacked: width < 900
    readonly property int minContentHeight: stacked ? (activeTabIndex === 0 ? 1280 : (activeTabIndex === 2 ? 1180 : 0)) : 0

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spaceMd

        // 1. Üst Başlık & Sekme Seçici (dar pencerede sekmeler başlığın altına geçer)
        GridLayout {
            Layout.fillWidth: true
            columns: root.width < 1060 ? 1 : 2
            columnSpacing: Theme.spaceMd
            rowSpacing: Theme.spaceSm

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                Text {
                    text: Strings.planningTitle
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXl
                    font.weight: Font.Bold
                }

                Text {
                    text: Strings.planningSubtitle
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                }
            }

            // 3 Sekmeli Segment Buton Grubu
            Rectangle {
                height: 40
                width: tabRow.width + Theme.spaceXs * 2
                radius: Theme.radiusSm
                color: Theme.bgCard
                border.color: Theme.borderCard
                border.width: 1

                Row {
                    id: tabRow
                    anchors.centerIn: parent
                    spacing: Theme.spaceXs

                    // Sekme 0: Bütçe
                    Rectangle {
                        width: 140
                        height: 32
                        radius: Theme.radiusXs
                        color: root.activeTabIndex === 0 ? Theme.accent : (btnTab0Mouse.containsMouse ? Theme.bgCardHover : "transparent")

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: Theme.spaceXs

                            ModernIcon {
                                name: "wallet"
                                color: root.activeTabIndex === 0 ? Theme.textInverse : Theme.textSecondary
                                size: 14
                            }

                            Text {
                                text: Strings.planningTabBudget
                                color: root.activeTabIndex === 0 ? Theme.textInverse : Theme.textPrimary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSm
                                font.weight: root.activeTabIndex === 0 ? Font.Bold : Font.Normal
                            }
                        }

                        MouseArea {
                            id: btnTab0Mouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.activeTabIndex = 0
                        }
                    }

                    // Sekme 1: Hedefler
                    Rectangle {
                        width: 140
                        height: 32
                        radius: Theme.radiusXs
                        color: root.activeTabIndex === 1 ? Theme.accent : (btnTab1Mouse.containsMouse ? Theme.bgCardHover : "transparent")

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: Theme.spaceXs

                            ModernIcon {
                                name: "target"
                                color: root.activeTabIndex === 1 ? Theme.textInverse : Theme.textSecondary
                                size: 14
                            }

                            Text {
                                text: Strings.planningTabGoals
                                color: root.activeTabIndex === 1 ? Theme.textInverse : Theme.textPrimary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSm
                                font.weight: root.activeTabIndex === 1 ? Font.Bold : Font.Normal
                            }
                        }

                        MouseArea {
                            id: btnTab1Mouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.activeTabIndex = 1
                        }
                    }

                    // Sekme 2: DCA
                    Rectangle {
                        width: 140
                        height: 32
                        radius: Theme.radiusXs
                        color: root.activeTabIndex === 2 ? Theme.accent : (btnTab2Mouse.containsMouse ? Theme.bgCardHover : "transparent")

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: Theme.spaceXs

                            ModernIcon {
                                name: "trendingup"
                                color: root.activeTabIndex === 2 ? Theme.textInverse : Theme.textSecondary
                                size: 14
                            }

                            Text {
                                text: Strings.planningTabDca
                                color: root.activeTabIndex === 2 ? Theme.textInverse : Theme.textPrimary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSm
                                font.weight: root.activeTabIndex === 2 ? Font.Bold : Font.Normal
                            }
                        }

                        MouseArea {
                            id: btnTab2Mouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.activeTabIndex = 2
                        }
                    }
                }
            }
        }

        // 2. Sekme İçerikleri (StackLayout)
        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.activeTabIndex

            // 0: Bütçe
            PlanningBudgetTab {
                id: budgetTab
            }

            // 1: Hedefler
            PlanningGoalsTab {
                id: goalsTab
                onNewGoalRequested: newGoalDialog.open()
                onEditGoalRequested: function(gId, gName, tAmt, dLine, prio) {
                    editGoalDialog.goalId = gId
                    editGoalDialog.goalName = gName
                    editGoalDialog.targetAmount = tAmt
                    editGoalDialog.deadline = dLine
                    editGoalDialog.priority = prio
                    editGoalDialog.open()
                }
                onContributeRequested: function(gId, gName, rem) {
                    contributionDialog.goalId = gId
                    contributionDialog.goalName = gName
                    contributionDialog.remainingFormatted = rem
                    contributionDialog.open()
                }
            }

            // 2: DCA
            PlanningDcaTab {
                id: dcaTab
            }
        }
    }

    // Toast Bildirim Kartı
    Rectangle {
        id: toastCard
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: root.toastVisible ? Theme.spaceMd : -60
        height: 38
        width: toastRow.width + Theme.spaceLg * 2
        radius: Theme.radiusFull
        color: root.toastSuccess ? Theme.bullGreenSoft : Theme.bearRedSoft
        border.color: root.toastSuccess ? Theme.bullGreen : Theme.bearRed
        border.width: 1
        visible: opacity > 0
        opacity: root.toastVisible ? 1.0 : 0.0

        Behavior on anchors.topMargin {
            NumberAnimation { duration: 250; easing.type: Easing.OutCubic }
        }
        Behavior on opacity {
            NumberAnimation { duration: 200 }
        }

        RowLayout {
            id: toastRow
            anchors.centerIn: parent
            spacing: Theme.spaceSm

            ModernIcon {
                name: root.toastSuccess ? "check" : "alert"
                color: root.toastSuccess ? Theme.bullGreen : Theme.bearRed
                size: 16
            }

            Text {
                text: root.toastMessage
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                font.weight: Font.DemiBold
            }
        }
    }

    // Dialoglar
    NewGoalDialog {
        id: newGoalDialog
    }

    EditGoalDialog {
        id: editGoalDialog
    }

    GoalContributionDialog {
        id: contributionDialog
    }
}
