import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Optimizasyon parametre paneli: kaynak portföy, risk profili, tek hisse ağırlık sınırı, risksiz faiz ve çalıştırma.
// SOL KONTROL PANELİ
Rectangle {
    id: root
    property bool stacked: false
    signal riskQuestionnaireRequested()
    Layout.fillWidth: root.stacked
    Layout.preferredWidth: root.stacked ? -1 : 290
    Layout.minimumWidth: root.stacked ? 0 : 270
    Layout.preferredHeight: root.stacked ? 430 : -1
    Layout.fillHeight: !root.stacked
    radius: Theme.radiusMd
    color: Theme.bgCard
    border.color: Theme.borderCard
    border.width: 1

    ScrollView {
        id: leftScroll
        anchors.fill: parent
        anchors.margins: Theme.spaceMd
        clip: true
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        ScrollBar.vertical: ModernScrollBar {}

        ColumnLayout {
            id: leftCol
            width: leftScroll.availableWidth
            spacing: 14

            // Başlık
            Text {
                text: Strings.optParamsTitle
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                font.weight: Font.Bold
                font.letterSpacing: 0.5
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: Theme.borderSubtle
            }

            // 1. Kaynak Portföy Seçici
            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceXs

                Text {
                    text: Strings.optSourcePortfolio
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    font.weight: Font.Medium
                }

                ComboBox {
                    id: portCombo
                    Layout.fillWidth: true
                    Layout.preferredHeight: 38
                    model: optimizationController.portfolioOptions
                    textRole: "label"

                    background: Rectangle {
                        color: portCombo.hovered ? Theme.bgCardHover : Theme.bgSecondary
                        border.color: portCombo.activeFocus ? Theme.accent : Theme.borderSubtle
                        border.width: 1
                        radius: Theme.radiusSm
                    }

                    contentItem: Text {
                        leftPadding: 10
                        rightPadding: 24
                        text: portCombo.displayText
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        color: Theme.textPrimary
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }

                    indicator: ModernIcon {
                        anchors.right: parent.right
                        anchors.rightMargin: 8
                        anchors.verticalCenter: parent.verticalCenter
                        name: "chevrondown"
                        size: 12
                        color: Theme.textMuted
                    }

                    popup: Popup {
                        y: portCombo.height + 2
                        width: portCombo.width
                        implicitHeight: Math.min(220, contentItem.implicitHeight + 8)
                        padding: 4

                        contentItem: ListView {
                            clip: true
                            implicitHeight: contentHeight
                            model: portCombo.popup.visible ? portCombo.delegateModel : null
                            currentIndex: portCombo.highlightedIndex
                        }

                        background: Rectangle {
                            color: Theme.bgCard
                            border.color: Theme.borderCard
                            border.width: 1
                            radius: Theme.radiusSm
                        }
                    }

                    delegate: ItemDelegate {
                        width: portCombo.width
                        height: 36
                        highlighted: portCombo.highlightedIndex === index

                        contentItem: Text {
                            text: modelData.label
                            color: highlighted ? Theme.accent : Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                        }

                        background: Rectangle {
                            color: highlighted ? Theme.accentSoft : "transparent"
                            radius: Theme.radiusXs
                        }
                    }

                    onActivated: function(idx) {
                        var opt = optimizationController.portfolioOptions[idx]
                        if (opt && opt.code) {
                            optimizationController.selectPortfolio(opt.code)
                        }
                    }
                }
            }

            // 2. Risk Profili Seçici
            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceXs

                Text {
                    text: Strings.optRiskProfile
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    font.weight: Font.Medium
                }

                ComboBox {
                    id: riskCombo
                    Layout.fillWidth: true
                    Layout.preferredHeight: 38
                    model: optimizationController.riskProfileOptions
                    textRole: "label"
                    currentIndex: {
                        const opts = optimizationController.riskProfileOptions
                        for (let i = 0; i < opts.length; i++) {
                            if (opts[i].code === optimizationController.selectedRiskProfile) return i
                        }
                        return 0
                    }

                    background: Rectangle {
                        color: riskCombo.hovered ? Theme.bgCardHover : Theme.bgSecondary
                        border.color: riskCombo.activeFocus ? Theme.accent : Theme.borderSubtle
                        border.width: 1
                        radius: Theme.radiusSm
                    }

                    contentItem: Text {
                        leftPadding: 10
                        rightPadding: 24
                        text: riskCombo.displayText
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        color: Theme.textPrimary
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }

                    indicator: ModernIcon {
                        anchors.right: parent.right
                        anchors.rightMargin: 8
                        anchors.verticalCenter: parent.verticalCenter
                        name: "chevrondown"
                        size: 12
                        color: Theme.textMuted
                    }

                    popup: Popup {
                        y: riskCombo.height + 2
                        width: riskCombo.width
                        implicitHeight: Math.min(240, contentItem.implicitHeight + 8)
                        padding: 4

                        contentItem: ListView {
                            clip: true
                            implicitHeight: contentHeight
                            model: riskCombo.popup.visible ? riskCombo.delegateModel : null
                            currentIndex: riskCombo.highlightedIndex
                        }

                        background: Rectangle {
                            color: Theme.bgCard
                            border.color: Theme.borderCard
                            border.width: 1
                            radius: Theme.radiusSm
                        }
                    }

                    delegate: ItemDelegate {
                        width: riskCombo.width
                        height: 36
                        highlighted: riskCombo.highlightedIndex === index

                        contentItem: Text {
                            text: modelData.label
                            color: highlighted ? Theme.accent : Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                        }

                        background: Rectangle {
                            color: highlighted ? Theme.accentSoft : "transparent"
                            radius: Theme.radiusXs
                        }
                    }

                    onActivated: function(idx) {
                        var opt = optimizationController.riskProfileOptions[idx]
                        if (opt && opt.code) {
                            optimizationController.selectRiskProfile(opt.code)
                        }
                    }
                }

                ModernButton {
                    Layout.fillWidth: true
                    text: Strings.riskBtnOpen
                    iconName: "shieldcheck"
                    variant: "secondary"
                    onClicked: root.riskQuestionnaireRequested()
                }
            }

            // 3. Tek Hisse Max Ağırlık Kısıtı
            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceXs

                RowLayout {
                    Layout.fillWidth: true

                    Text {
                        text: Strings.optMaxSingleWeight
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        font.weight: Font.Medium
                    }

                    Item { Layout.fillWidth: true }

                    Rectangle {
                        width: weightValText.width + 16
                        height: 24
                        radius: Theme.radiusXs
                        color: Theme.accentSoft

                        Text {
                            id: weightValText
                            anchors.centerIn: parent
                            text: "%" + Math.round(optimizationController.maxSingleWeight)
                            color: Theme.accent
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.Bold
                        }
                    }
                }

                Slider {
                    id: weightSlider
                    Layout.fillWidth: true
                    from: 5
                    to: 50
                    stepSize: 1
                    value: optimizationController.maxSingleWeight

                    onMoved: {
                        optimizationController.setMaxSingleWeight(value)
                    }
                }
            }

            // 4. Risksiz Faiz Oranı Kısıtı
            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceXs

                RowLayout {
                    Layout.fillWidth: true

                    Text {
                        text: Strings.optRiskFreeRate
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        font.weight: Font.Medium
                    }

                    Item { Layout.fillWidth: true }

                    Rectangle {
                        width: rfValText.width + 16
                        height: 24
                        radius: Theme.radiusXs
                        color: Theme.bgSecondary
                        border.color: Theme.borderSubtle
                        border.width: 1

                        Text {
                            id: rfValText
                            anchors.centerIn: parent
                            text: "%" + Math.round(optimizationController.riskFreeRate)
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.DemiBold
                        }
                    }
                }

                Slider {
                    id: rfSlider
                    Layout.fillWidth: true
                    from: 0
                    to: 60
                    stepSize: 1
                    value: optimizationController.riskFreeRate

                    onMoved: {
                        optimizationController.setRiskFreeRate(value)
                    }
                }
            }

            // Bilgi Notu
            Rectangle {
                Layout.fillWidth: true
                radius: Theme.radiusSm
                color: Theme.bgSecondary
                border.color: Theme.borderSubtle
                border.width: 1
                implicitHeight: infoCol.implicitHeight + 20

                ColumnLayout {
                    id: infoCol
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 10
                    spacing: 6

                    RowLayout {
                        spacing: 6
                        ModernIcon {
                            name: "info"
                            size: 14
                            color: Theme.accent
                        }
                        Text {
                            text: Strings.optMptTitle
                            color: Theme.accent
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.DemiBold
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: Strings.optMptDescription
                        color: Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: 12
                        lineHeight: 1.3
                    }
                }
            }

            // Durum Mesajı
            Rectangle {
                Layout.fillWidth: true
                visible: optimizationController.statusMessage !== ""
                radius: Theme.radiusSm
                color: optimizationController.hasResults ? Theme.bullGreenSoft : (optimizationController.statusMessage.indexOf("Hata") !== -1 ? Theme.bearRedSoft : Theme.warningYellowSoft)
                border.color: optimizationController.hasResults ? Theme.bullGreen : (optimizationController.statusMessage.indexOf("Hata") !== -1 ? Theme.bearRed : Theme.warningYellow)
                border.width: 1
                implicitHeight: statusText.implicitHeight + 18

                Text {
                    id: statusText
                    anchors.fill: parent
                    anchors.margins: 10
                    wrapMode: Text.WordWrap
                    text: optimizationController.statusMessage
                    color: optimizationController.hasResults ? Theme.bullGreen : (optimizationController.statusMessage.indexOf("Hata") !== -1 ? Theme.bearRed : Theme.warningYellow)
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    verticalAlignment: Text.AlignVCenter
                }
            }

            // Çalıştır Butonu
            Rectangle {
                Layout.fillWidth: true
                height: 48
                radius: Theme.radiusSm
                color: btnRunMouse.containsMouse ? Theme.accentHover : Theme.accent
                opacity: optimizationController.isLoading ? 0.7 : 1.0

                RowLayout {
                    anchors.centerIn: parent
                    spacing: Theme.spaceSm

                    ModernIcon {
                        name: "refresh"
                        color: Theme.textInverse
                        size: 18
                        visible: !optimizationController.isLoading
                    }

                    BusyIndicator {
                        width: 20
                        height: 20
                        running: optimizationController.isLoading
                        visible: optimizationController.isLoading
                    }

                    Text {
                        text: optimizationController.isLoading ? Strings.btnCalculating : Strings.optBtnRun
                        color: Theme.textInverse
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        font.weight: Font.Bold
                    }
                }

                MouseArea {
                    id: btnRunMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    enabled: !optimizationController.isLoading
                    onClicked: optimizationController.runOptimization()
                }
            } // btnRun
        } // leftCol
    } // leftScroll
} // Rectangle (sol panel)
