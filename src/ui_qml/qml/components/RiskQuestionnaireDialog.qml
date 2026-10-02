import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Risk profili anketi: bölüm bölüm sorular, puanlama ve kayıtlı profil özeti.
Rectangle {
    id: root

    property bool isOpen: false
    property bool showResult: false
    property int step: 0
    property var answers: ({})
    property string statusText: ""
    property bool statusIsError: false

    readonly property bool hasController: typeof riskProfileController !== "undefined"
    readonly property var sections: hasController ? riskProfileController.sections : []
    readonly property var profile: hasController ? riskProfileController.profile : ({ exists: false })
    readonly property bool isLastStep: step >= sections.length - 1
    readonly property bool stepComplete: {
        if (step < 0 || step >= sections.length) return false
        const qs = sections[step].questions
        for (let i = 0; i < qs.length; i++) {
            if (answers[qs[i].id] === undefined) return false
        }
        return true
    }

    signal saved()

    anchors.fill: parent
    color: "#99000000"
    visible: opacity > 0
    opacity: isOpen ? 1.0 : 0.0
    z: 1000

    Behavior on opacity { NumberAnimation { duration: 180 } }

    function open() {
        statusText = ""
        step = 0
        answers = (profile.exists && profile.answers) ? Object.assign({}, profile.answers) : ({})
        showResult = profile.exists === true
        isOpen = true
    }

    function close() {
        isOpen = false
    }

    function selectAnswer(questionId, value) {
        const next = Object.assign({}, answers)
        next[questionId] = value
        answers = next
    }

    Connections {
        target: root.hasController ? riskProfileController : null
        function onNotification(success, message) {
            if (!root.isOpen) return
            root.statusText = message
            root.statusIsError = !success
        }
    }

    MouseArea {
        anchors.fill: parent
        onClicked: root.close()
    }

    ModernCard {
        anchors.centerIn: parent
        width: Math.min(720, root.width - 32)
        height: Math.min(root.height - 32, 680)

        MouseArea { anchors.fill: parent }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Theme.spaceLg
            spacing: Theme.spaceMd

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: Strings.riskTitle
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontMd
                    font.weight: Font.Bold
                    color: Theme.textPrimary
                    Layout.fillWidth: true
                }
                Item {
                    width: 24
                    height: 24
                    ModernIcon { name: "close"; size: 16; color: Theme.textMuted; anchors.centerIn: parent }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.close()
                    }
                }
            }

            // ---------------- Sonuç görünümü ----------------
            Flickable {
                visible: root.showResult && root.profile.exists === true
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentWidth: width
                contentHeight: resultColumn.implicitHeight
                clip: true
                ScrollBar.vertical: ModernScrollBar {}

                ColumnLayout {
                    id: resultColumn
                    width: parent.width
                    spacing: Theme.spaceMd

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: scoreFlow.implicitHeight + Theme.spaceMd * 2
                        radius: Theme.radiusSm
                        color: Theme.accentSoft
                        border.color: Theme.accent

                        Flow {
                            id: scoreFlow
                            anchors.fill: parent
                            anchors.margins: Theme.spaceMd
                            spacing: Theme.spaceLg

                            Column {
                                spacing: 2
                                Text { text: Strings.riskScoreLabel; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.Bold }
                                Text { text: root.profile.score + " / 100"; color: Theme.textPrimary; font.family: Theme.fontMono; font.pixelSize: Theme.fontXl; font.weight: Font.Bold }
                            }
                            Column {
                                spacing: 2
                                Text { text: Strings.riskProfileLabel; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.Bold }
                                Text { text: root.profile.labelText; color: Theme.accent; font.family: Theme.fontFamily; font.pixelSize: Theme.fontLg; font.weight: Font.Bold }
                            }
                        }
                    }

                    Text {
                        text: root.profile.description
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }

                    Text { text: Strings.riskDimensions; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.Bold }

                    Repeater {
                        model: root.profile.dimensions
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spaceSm
                            Text { text: modelData.name; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm; Layout.preferredWidth: 150; elide: Text.ElideRight }
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 8
                                radius: 4
                                color: Theme.borderSubtle
                                Rectangle {
                                    width: parent.width * Math.max(0, Math.min(100, modelData.score)) / 100
                                    height: parent.height
                                    radius: 4
                                    color: Theme.accent
                                }
                            }
                            Text { text: modelData.score + " / 100"; color: Theme.textPrimary; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; Layout.preferredWidth: 70; horizontalAlignment: Text.AlignRight }
                        }
                    }

                    Text { text: Strings.riskAllocation; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.Bold }

                    Flow {
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm
                        Repeater {
                            model: root.profile.allocation
                            Rectangle {
                                width: allocText.implicitWidth + 20
                                height: 30
                                radius: Theme.radiusSm
                                color: Theme.bgSecondary
                                border.color: Theme.borderSubtle
                                Text {
                                    id: allocText
                                    anchors.centerIn: parent
                                    text: modelData.asset + ": %" + modelData.weight
                                    color: Theme.textPrimary
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSm
                                }
                            }
                        }
                    }

                    Text {
                        visible: root.profile.notes && root.profile.notes.length > 0
                        text: root.profile.notes ? root.profile.notes.join("\n") : ""
                        color: Theme.warning
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
            }

            // ---------------- Anket görünümü ----------------
            ColumnLayout {
                visible: !(root.showResult && root.profile.exists === true)
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: Theme.spaceSm

                Text {
                    text: root.sections.length > 0
                          ? Strings.riskStepTmpl.replace("%1", root.step + 1).replace("%2", root.sections.length) + " — " + root.sections[root.step].title
                          : Strings.riskNoQuestionnaire
                    color: Theme.accent
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    font.weight: Font.DemiBold
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                Flickable {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    contentWidth: width
                    contentHeight: questionColumn.implicitHeight
                    clip: true
                    ScrollBar.vertical: ModernScrollBar {}

                    ColumnLayout {
                        id: questionColumn
                        width: parent.width
                        spacing: Theme.spaceMd

                        Repeater {
                            model: root.sections.length > 0 ? root.sections[root.step].questions : []

                            ColumnLayout {
                                id: questionItem
                                readonly property var question: modelData
                                Layout.fillWidth: true
                                spacing: Theme.spaceXs

                                Text {
                                    text: (index + 1) + ". " + modelData.title
                                    color: Theme.textPrimary
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontBase
                                    font.weight: Font.DemiBold
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                }

                                Repeater {
                                    model: modelData.options

                                    Rectangle {
                                        readonly property bool chosen: root.answers[questionItem.question.id] === modelData.value
                                        Layout.fillWidth: true
                                        implicitHeight: optionText.implicitHeight + 16
                                        radius: Theme.radiusSm
                                        color: chosen ? Theme.accentSoft : (optionMouse.containsMouse ? Theme.bgCardHover : Theme.bgSecondary)
                                        border.color: chosen ? Theme.accent : Theme.borderSubtle

                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: Theme.spaceSm
                                            anchors.rightMargin: Theme.spaceSm
                                            spacing: Theme.spaceSm

                                            Rectangle {
                                                width: 16
                                                height: 16
                                                radius: 8
                                                color: "transparent"
                                                border.color: chosen ? Theme.accent : Theme.textMuted
                                                border.width: 2
                                                Rectangle {
                                                    anchors.centerIn: parent
                                                    width: 8
                                                    height: 8
                                                    radius: 4
                                                    color: Theme.accent
                                                    visible: chosen
                                                }
                                            }

                                            Text {
                                                id: optionText
                                                text: modelData.label
                                                color: Theme.textPrimary
                                                font.family: Theme.fontFamily
                                                font.pixelSize: Theme.fontSm
                                                wrapMode: Text.WordWrap
                                                Layout.fillWidth: true
                                            }
                                        }

                                        MouseArea {
                                            id: optionMouse
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: root.selectAnswer(questionItem.question.id, modelData.value)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Text {
                visible: root.statusText !== ""
                text: root.statusText
                color: root.statusIsError ? Theme.bearRed : Theme.bullGreen
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            // ---------------- Alt butonlar ----------------
            Flow {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                layoutDirection: Qt.RightToLeft

                ModernButton {
                    visible: root.showResult && root.profile.exists === true
                    text: Strings.riskBtnRetake
                    variant: "primary"
                    onClicked: {
                        root.statusText = ""
                        root.showResult = false
                        root.step = 0
                    }
                }

                ModernButton {
                    visible: !(root.showResult && root.profile.exists === true) && !root.isLastStep
                    text: Strings.riskBtnNext
                    variant: "primary"
                    enabled: root.stepComplete
                    onClicked: { root.statusText = ""; root.step = root.step + 1 }
                }

                ModernButton {
                    visible: !(root.showResult && root.profile.exists === true) && root.isLastStep
                    text: Strings.riskBtnCalculate
                    variant: "primary"
                    enabled: root.stepComplete && root.hasController && !riskProfileController.isBusy
                    onClicked: {
                        if (riskProfileController.calculate(root.answers)) {
                            root.showResult = true
                            root.saved()
                        }
                    }
                }

                ModernButton {
                    visible: !(root.showResult && root.profile.exists === true) && root.step > 0
                    text: Strings.riskBtnBack
                    variant: "secondary"
                    onClicked: { root.statusText = ""; root.step = root.step - 1 }
                }

                ModernButton {
                    text: Strings.btnClose
                    variant: "secondary"
                    onClicked: root.close()
                }
            }
        }
    }
}
