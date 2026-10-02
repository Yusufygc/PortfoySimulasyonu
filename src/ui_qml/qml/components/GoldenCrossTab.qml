import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Hisse Tarayıcı > Golden Cross sekmesi: EMA50/EMA200 kesişim sinyalleri, tarama ve hisse bazlı geçmiş.
Item {
    id: root

    readonly property bool hasController: typeof goldenCrossController !== "undefined"
    readonly property bool busy: hasController && goldenCrossController.isBusy
    readonly property bool wide: width >= 900
    readonly property bool showMaColumn: tableCard.width >= 560

    property string selectedTicker: ""

    // Üst Hisse Tarayıcı toast'ı
    signal notify(bool success, string message)

    function currentDays() {
        const opts = goldenCrossController.periodOptions
        return opts[periodCombo.currentIndex] ? opts[periodCombo.currentIndex].days : 30
    }

    function currentType() {
        const opts = goldenCrossController.typeOptions
        return opts[typeCombo.currentIndex] ? opts[typeCombo.currentIndex].key : ""
    }

    function reload() {
        if (hasController) goldenCrossController.refresh(currentDays(), currentType())
    }

    function openChart(ticker) {
        if (typeof chartController !== "undefined") chartController.loadTicker(ticker)
        if (typeof shellController !== "undefined") shellController.navigateTo(0)
    }

    Component.onCompleted: reload()

    Connections {
        target: root.hasController ? goldenCrossController : null
        function onScanCompleted() { root.reload() }
        function onNotification(success, message) { root.notify(success, message) }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spaceMd

        // Filtre ve aksiyon kartı
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: controlFlow.implicitHeight + Theme.spaceMd * 2
            color: Theme.bgCard
            radius: Theme.radiusMd
            border.color: Theme.borderCard
            border.width: 1

            Flow {
                id: controlFlow
                anchors.fill: parent
                anchors.margins: Theme.spaceMd
                spacing: Theme.spaceMd

                Row {
                    spacing: Theme.spaceXs
                    height: 36
                    Text {
                        text: Strings.gcPeriod + ":"
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        font.weight: Font.DemiBold
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    ModernComboBox {
                        id: periodCombo
                        width: 120
                        height: 36
                        model: root.hasController ? goldenCrossController.periodOptions : []
                        textRole: "label"
                        currentIndex: 1
                        onActivated: root.reload()
                    }
                }

                Row {
                    spacing: Theme.spaceXs
                    height: 36
                    Text {
                        text: Strings.gcType + ":"
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        font.weight: Font.DemiBold
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    ModernComboBox {
                        id: typeCombo
                        width: 120
                        height: 36
                        model: root.hasController ? goldenCrossController.typeOptions : []
                        textRole: "label"
                        onActivated: root.reload()
                    }
                }

                ModernButton {
                    text: Strings.gcBtnRefresh
                    iconName: "refresh"
                    variant: "secondary"
                    implicitHeight: 36
                    onClicked: root.reload()
                }

                ModernButton {
                    text: Strings.gcBtnScan
                    iconName: "play"
                    variant: "primary"
                    implicitHeight: 36
                    enabled: root.hasController && goldenCrossController.serviceAvailable && !root.busy
                    onClicked: goldenCrossController.scanAll()
                }

                ModernButton {
                    text: Strings.gcBtnCompleteData
                    variant: "secondary"
                    implicitHeight: 36
                    enabled: root.hasController && !root.busy
                    onClicked: goldenCrossController.completeData()
                }

                Row {
                    spacing: Theme.spaceXs
                    height: 36
                    visible: root.busy
                    BusyIndicator {
                        running: root.busy
                        implicitWidth: 22
                        implicitHeight: 22
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        text: root.hasController ? goldenCrossController.busyText : ""
                        color: Theme.accent
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
            }
        }

        // İçerik: sinyal tablosu + hisse detayı (geniş ekranda yan yana, dar ekranda alt alta)
        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: root.wide ? 2 : 1
            columnSpacing: Theme.spaceMd
            rowSpacing: Theme.spaceMd

            // Sinyal tablosu
            Rectangle {
                id: tableCard
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredWidth: 3
                Layout.minimumHeight: 200
                color: Theme.bgCard
                radius: Theme.radiusMd
                border.color: Theme.borderCard
                border.width: 1
                clip: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spaceMd
                    spacing: Theme.spaceSm

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: Strings.gcSignalsTitle
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.DemiBold
                            font.letterSpacing: 0.5
                            Layout.fillWidth: true
                        }
                        Text {
                            text: root.hasController ? goldenCrossController.status : ""
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            elide: Text.ElideLeft
                            Layout.maximumWidth: tableCard.width * 0.6
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 32
                        color: Theme.bgSecondary
                        radius: Theme.radiusSm

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.spaceMd
                            anchors.rightMargin: Theme.spaceMd
                            spacing: Theme.spaceSm

                            Text { text: Strings.gcThDate; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold; Layout.preferredWidth: 90 }
                            Text { text: Strings.gcThTicker; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold; Layout.preferredWidth: 80 }
                            Text { text: Strings.gcThType; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold; Layout.fillWidth: true }
                            Text { text: Strings.gcThClose; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignRight; Layout.preferredWidth: 90 }
                            Text { visible: root.showMaColumn; text: Strings.gcThMa; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignRight; Layout.preferredWidth: 130 }
                        }
                    }

                    ListView {
                        id: eventList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 2
                        model: root.hasController ? goldenCrossController.events : []
                        ScrollBar.vertical: ModernScrollBar {}

                        delegate: Rectangle {
                            width: eventList.width
                            height: 36
                            radius: Theme.radiusSm
                            color: modelData.ticker === root.selectedTicker
                                   ? Theme.accentSoft
                                   : (rowMouse.containsMouse ? Theme.bgCardHover : (index % 2 === 0 ? "transparent" : Theme.bgSecondary))

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: Theme.spaceMd
                                anchors.rightMargin: Theme.spaceMd
                                spacing: Theme.spaceSm

                                Text { text: modelData.date; color: Theme.textSecondary; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; Layout.preferredWidth: 90 }
                                Text { text: modelData.ticker; color: Theme.accent; font.family: Theme.fontFamily; font.pixelSize: Theme.fontBase; font.weight: Font.Bold; Layout.preferredWidth: 80 }
                                Text {
                                    text: (modelData.isGolden ? "▲ " : "▼ ") + modelData.typeLabel
                                    color: modelData.isGolden ? Theme.bullGreen : Theme.bearRed
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSm
                                    font.weight: Font.DemiBold
                                    Layout.fillWidth: true
                                }
                                Text { text: modelData.close; color: Theme.textPrimary; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; horizontalAlignment: Text.AlignRight; Layout.preferredWidth: 90 }
                                Text { visible: root.showMaColumn; text: modelData.ma; color: Theme.textSecondary; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; horizontalAlignment: Text.AlignRight; Layout.preferredWidth: 130 }
                            }

                            MouseArea {
                                id: rowMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    root.selectedTicker = modelData.ticker
                                    goldenCrossController.loadTickerEvents(modelData.ticker)
                                }
                                onDoubleClicked: root.openChart(modelData.ticker)
                            }
                        }

                        Text {
                            anchors.centerIn: parent
                            visible: eventList.count === 0
                            width: parent.width - Theme.spaceLg
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.WordWrap
                            text: Strings.gcEmpty
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                        }
                    }
                }
            }

            // Hisse bazlı kesişim geçmişi
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredWidth: 2
                Layout.minimumHeight: 200
                color: Theme.bgCard
                radius: Theme.radiusMd
                border.color: Theme.borderCard
                border.width: 1
                clip: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spaceMd
                    spacing: Theme.spaceSm

                    Flow {
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm

                        Text {
                            height: 34
                            verticalAlignment: Text.AlignVCenter
                            text: Strings.gcDetailTitle
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.DemiBold
                            font.letterSpacing: 0.5
                        }

                        ModernInput {
                            id: txtTicker
                            width: 110
                            placeholder: Strings.gcTickerPlaceholder
                            text: root.selectedTicker
                            onAccepted: goldenCrossController.loadTickerEvents(text)
                        }

                        ModernButton {
                            text: Strings.gcBtnShow
                            variant: "secondary"
                            onClicked: {
                                root.selectedTicker = txtTicker.text.trim().toUpperCase()
                                goldenCrossController.loadTickerEvents(txtTicker.text)
                            }
                        }

                        ModernButton {
                            text: Strings.btnChart
                            variant: "ghost"
                            enabled: root.selectedTicker !== ""
                            onClicked: root.openChart(root.selectedTicker)
                        }
                    }

                    ListView {
                        id: tickerList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 2
                        model: root.hasController ? goldenCrossController.tickerEvents : []
                        ScrollBar.vertical: ModernScrollBar {}

                        delegate: Rectangle {
                            width: tickerList.width
                            height: 34
                            radius: Theme.radiusSm
                            color: index % 2 === 0 ? "transparent" : Theme.bgSecondary

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: Theme.spaceMd
                                anchors.rightMargin: Theme.spaceMd
                                spacing: Theme.spaceSm

                                Text { text: modelData.date; color: Theme.textSecondary; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; Layout.preferredWidth: 90 }
                                Text {
                                    text: (modelData.isGolden ? "▲ " : "▼ ") + modelData.typeLabel
                                    color: modelData.isGolden ? Theme.bullGreen : Theme.bearRed
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSm
                                    font.weight: Font.DemiBold
                                    Layout.fillWidth: true
                                }
                                Text { text: modelData.close; color: Theme.textPrimary; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; horizontalAlignment: Text.AlignRight; Layout.preferredWidth: 90 }
                            }
                        }

                        Text {
                            anchors.centerIn: parent
                            visible: tickerList.count === 0
                            width: parent.width - Theme.spaceLg
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.WordWrap
                            text: Strings.gcDetailEmpty
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                        }
                    }
                }
            }
        }
    }
}
