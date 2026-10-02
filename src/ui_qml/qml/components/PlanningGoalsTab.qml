import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

Item {
    id: root

    signal newGoalRequested()
    signal editGoalRequested(int goalId, string name, real targetAmount, string deadline, string priority)
    signal contributeRequested(int goalId, string goalName, string remaining)

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spaceMd

        // 1. Üst Bar: Fizibilite Özeti & Yeni Hedef Butonu
        Rectangle {
            Layout.fillWidth: true
            height: 72
            color: Theme.bgCard
            radius: Theme.radiusMd
            border.color: Theme.borderCard
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.margins: Theme.spaceMd
                spacing: Theme.spaceLg

                // Fizibilite Durumu Rozeti
                RowLayout {
                    spacing: Theme.spaceSm

                    Rectangle {
                        width: 38
                        height: 38
                        radius: Theme.radiusSm
                        color: planningController.feasibilityStatus === "BAŞARILI" ? Theme.bullGreenSoft : Theme.warningYellow

                        ModernIcon {
                            anchors.centerIn: parent
                            name: planningController.feasibilityStatus === "BAŞARILI" ? "shieldcheck" : "alert"
                            color: planningController.feasibilityStatus === "BAŞARILI" ? Theme.bullGreen : Theme.textPrimary
                            size: 18
                        }
                    }

                    ColumnLayout {
                        spacing: 2
                        Text {
                            text: Strings.goalsFeasibilityTitle + ": " + planningController.feasibilityStatus
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBase
                            font.weight: Font.Bold
                        }
                        Text {
                            text: planningController.feasibilityMessage || Strings.goalsFeasibilityHint
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                        }
                    }
                }

                Item { Layout.fillWidth: true }

                // Metrikler
                ColumnLayout {
                    spacing: 2
                    Text {
                        text: Strings.goalsFeasibilityNeed
                        color: Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                    }
                    Text {
                        text: planningController.totalMonthlyNeedFormatted
                        color: Theme.textPrimary
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontBase
                        font.weight: Font.Bold
                    }
                }

                ColumnLayout {
                    spacing: 2
                    Text {
                        text: Strings.goalsFeasibilityPower
                        color: Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                    }
                    Text {
                        text: planningController.monthlyPowerFormatted
                        color: Theme.bullGreen
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontBase
                        font.weight: Font.Bold
                    }
                }

                // Yeni Hedef Butonu
                Rectangle {
                    width: 120
                    height: 36
                    radius: Theme.radiusSm
                    color: btnNewGoalMouse.containsMouse ? Theme.accentHover : Theme.accent

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: Theme.spaceXs

                        ModernIcon {
                            name: "plus"
                            color: Theme.textInverse
                            size: 14
                        }

                        Text {
                            text: Strings.goalsBtnNew
                            color: Theme.textInverse
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.DemiBold
                        }
                    }

                    MouseArea {
                        id: btnNewGoalMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.newGoalRequested()
                    }
                }
            }
        }

        // 2. Hedefler Listesi
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ListView {
                id: goalsListView
                anchors.fill: parent
                clip: true
                spacing: Theme.spaceSm
                model: planningController.goalsList
                visible: planningController.goalsList.length > 0

                ScrollBar.vertical: ModernScrollBar {}

                delegate: Rectangle {
                    width: goalsListView.width
                    height: 104
                    radius: Theme.radiusMd
                    color: Theme.bgCard
                    border.color: Theme.borderCard
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: Theme.spaceMd
                        spacing: Theme.spaceSm

                        // Üst Satır: İsim, Rozetler ve Aksiyonlar
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spaceSm

                            ModernIcon {
                                name: "target"
                                color: modelData.isCompleted ? Theme.bullGreen : Theme.accent
                                size: 18
                            }

                            Text {
                                text: modelData.name
                                color: Theme.textPrimary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontBase
                                font.weight: Font.Bold
                            }

                            // Öncelik Rozeti
                            Rectangle {
                                height: 18
                                width: pText.width + 10
                                radius: Theme.radiusXs
                                color: (modelData.priority === "HIGH" || modelData.priorityTr === "YÜKSEK") ? Theme.bearRedSoft : ((modelData.priority === "MEDIUM" || modelData.priorityTr === "ORTA") ? Theme.accentSoft : Theme.bgSecondary)

                                Text {
                                    id: pText
                                    anchors.centerIn: parent
                                    text: modelData.priorityTr || (modelData.priority === "HIGH" ? Strings.goalPriorityHigh : (modelData.priority === "LOW" ? Strings.goalPriorityLow : Strings.goalPriorityMedium))
                                    color: (modelData.priority === "HIGH" || modelData.priorityTr === "YÜKSEK") ? Theme.bearRed : ((modelData.priority === "MEDIUM" || modelData.priorityTr === "ORTA") ? Theme.accent : Theme.textMuted)
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 10
                                    font.weight: Font.Bold
                                }
                            }

                            // Tamamlandı Rozeti
                            Rectangle {
                                height: 18
                                width: compText.width + 10
                                radius: Theme.radiusXs
                                color: Theme.bullGreenSoft
                                visible: modelData.isCompleted

                                Text {
                                    id: compText
                                    anchors.centerIn: parent
                                    text: Strings.goalCompletedBadge
                                    color: Theme.bullGreen
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 10
                                    font.weight: Font.Bold
                                }
                            }

                            Item { Layout.fillWidth: true }

                            // Hedef Tarih
                            Text {
                                text: Strings.goalTargetPrefix + modelData.deadline
                                color: Theme.textMuted
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                            }

                            // Katkı Yap Butonu
                            Rectangle {
                                width: 90
                                height: 28
                                radius: Theme.radiusSm
                                color: btnContrMouse.containsMouse ? Theme.bullGreen : Theme.bullGreenSoft
                                visible: !modelData.isCompleted

                                RowLayout {
                                    anchors.centerIn: parent
                                    spacing: 4

                                    ModernIcon {
                                        name: "coins"
                                        color: btnContrMouse.containsMouse ? Theme.textInverse : Theme.bullGreen
                                        size: 12
                                    }

                                    Text {
                                        text: Strings.goalsBtnContribute
                                        color: btnContrMouse.containsMouse ? Theme.textInverse : Theme.bullGreen
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontXs
                                        font.weight: Font.DemiBold
                                    }
                                }

                                MouseArea {
                                    id: btnContrMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.contributeRequested(modelData.id, modelData.name, modelData.remainingAmountFormatted)
                                }
                            }

                            // Düzenle Butonu
                            Rectangle {
                                width: 28
                                height: 28
                                radius: Theme.radiusXs
                                color: btnEditMouse.containsMouse ? Theme.accentSoft : "transparent"

                                ModernIcon {
                                    anchors.centerIn: parent
                                    name: "edit"
                                    color: btnEditMouse.containsMouse ? Theme.accent : Theme.textMuted
                                    size: 13
                                }

                                MouseArea {
                                    id: btnEditMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.editGoalRequested(modelData.id, modelData.name, modelData.targetAmount, modelData.deadline, modelData.priorityTr || modelData.priority)
                                }
                            }

                            // Sil Butonu
                            Rectangle {
                                width: 28
                                height: 28
                                radius: Theme.radiusXs
                                color: btnDelMouse.containsMouse ? Theme.bearRedSoft : "transparent"

                                ModernIcon {
                                    anchors.centerIn: parent
                                    name: "trash"
                                    color: btnDelMouse.containsMouse ? Theme.bearRed : Theme.textMuted
                                    size: 13
                                }

                                MouseArea {
                                    id: btnDelMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: planningController.deleteGoal(modelData.id)
                                }
                            }
                        }

                        // İlerleme Çubuğu
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spaceSm

                            Rectangle {
                                Layout.fillWidth: true
                                height: 8
                                radius: 4
                                color: Theme.bgSecondary

                                Rectangle {
                                    anchors.left: parent.left
                                    anchors.top: parent.top
                                    anchors.bottom: parent.bottom
                                    width: Math.min(parent.width, parent.width * modelData.progress)
                                    radius: 4
                                    color: modelData.isCompleted ? Theme.bullGreen : Theme.accent
                                }
                            }

                            Text {
                                text: modelData.progressPct
                                color: modelData.isCompleted ? Theme.bullGreen : Theme.accent
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSm
                                font.weight: Font.Bold
                                Layout.preferredWidth: 50
                                horizontalAlignment: Text.AlignRight
                            }
                        }

                        // Alt Tutar Bilgileri
                        RowLayout {
                            Layout.fillWidth: true

                            Text {
                                text: Strings.goalSavedPrefix + modelData.currentAmountFormatted
                                color: Theme.textSecondary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                            }

                            Text {
                                text: "•"
                                color: Theme.textMuted
                                font.pixelSize: Theme.fontXs
                            }

                            Text {
                                text: Strings.goalTargetPrefix + modelData.targetAmountFormatted
                                color: Theme.textSecondary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                            }

                            Text {
                                text: "•"
                                color: Theme.textMuted
                                font.pixelSize: Theme.fontXs
                            }

                            Text {
                                text: Strings.goalRemainingPrefix + modelData.remainingAmountFormatted
                                color: Theme.bearRed
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                            }

                            Item { Layout.fillWidth: true }

                            Text {
                                text: Strings.goalMonthlyNeededPrefix + modelData.requiredMonthlyFormatted
                                color: Theme.textMuted
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                            }
                        }
                    }
                }
            }

            // Boş Durum
            ColumnLayout {
                anchors.centerIn: parent
                visible: planningController.goalsList.length === 0
                spacing: Theme.spaceSm

                ModernIcon {
                    Layout.alignment: Qt.AlignHCenter
                    name: "target"
                    color: Theme.textMuted
                    size: 44
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: Strings.goalsEmptyTitle
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    font.weight: Font.DemiBold
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: Strings.goalsEmptyHint
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                }

                Rectangle {
                    Layout.alignment: Qt.AlignHCenter
                    width: 130
                    height: 36
                    radius: Theme.radiusSm
                    color: Theme.accent

                    Text {
                        anchors.centerIn: parent
                        text: Strings.goalsBtnNew
                        color: Theme.textInverse
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        font.weight: Font.DemiBold
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.newGoalRequested()
                    }
                }
            }
        }
    }
}
