import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import QtWebEngine
import "../theme"
import "../components"

Rectangle {
    id: root

    color: Theme.bgPrimary

    // Dar pencerede parametre paneli üstte, sonuçlar altta (ana sayfa kaydırması devreye girer)
    readonly property bool stacked: width < 980
    readonly property int minContentHeight: stacked ? 1300 : 0

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spaceLg
        spacing: Theme.spaceMd

        // 1. Sayfa Başlığı ve Açıklama
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            Rectangle {
                width: 38
                height: 38
                radius: Theme.radiusMd
                color: Theme.accentSoft

                ModernIcon {
                    anchors.centerIn: parent
                    name: "optimization"
                    size: 20
                    color: Theme.accent
                }
            }

            ColumnLayout {
                spacing: 2

                Text {
                    text: Strings.optTitle
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXl
                    font.weight: Font.Bold
                }

                Text {
                    text: Strings.optSubtitle
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                }
            }

            Item { Layout.fillWidth: true }
        }

        // 2. Ana Çalışma Alanı (Sol Panel: Parametreler | Sağ Panel: KPI + Grafikler/Tablolar)
        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: root.stacked ? 1 : 2
            columnSpacing: Theme.spaceMd
            rowSpacing: Theme.spaceMd

            // SOL KONTROL PANELİ
            Rectangle {
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
                            text: "OPTİMİZASYON PARAMETRELERİ"
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
                                onClicked: riskQuestionnaire.open()
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
                                        text: "Modern Portföy Teorisi (MPT)"
                                        color: Theme.accent
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSm
                                        font.weight: Font.DemiBold
                                    }
                                }

                                Text {
                                    Layout.fillWidth: true
                                    wrapMode: Text.WordWrap
                                    text: "Ledoit-Wolf kovaryans daraltması ve SciPy SLSQP çözücüsü ile portföyün risk başına getirisini (Sharpe) maksimize eder."
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
                                    text: optimizationController.isLoading ? "Hesaplanıyor..." : Strings.optBtnRun
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

            // SAĞ ANA ALAN (KPI + Sekmeler + Grafik / Tablo)
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredHeight: 780
                spacing: Theme.spaceMd

                // 1. KPI ŞERİDİ (4 KART; dar alanda 2x2)
                GridLayout {
                    Layout.fillWidth: true
                    columns: (root.stacked ? root.width < 800 : root.width < 1280) ? 2 : 4
                    columnSpacing: Theme.spaceMd
                    rowSpacing: Theme.spaceMd
                    uniformCellWidths: true

                    // Kart 1: Maksimum Sharpe
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 88
                        radius: Theme.radiusMd
                        color: Theme.bgCard
                        border.color: Theme.borderCard
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            anchors.topMargin: 10
                            anchors.bottomMargin: 10
                            spacing: Theme.spaceSm

                            Rectangle {
                                width: 36
                                height: 36
                                radius: Theme.radiusSm
                                color: Theme.accentSoft

                                ModernIcon {
                                    anchors.centerIn: parent
                                    name: "target"
                                    color: Theme.accent
                                    size: 18
                                }
                            }

                            ColumnLayout {
                                spacing: 2
                                Text {
                                    text: Strings.optKpiSharpe
                                    color: Theme.textMuted
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                }
                                Text {
                                    text: optimizationController.optimalSharpeFormatted
                                    color: optimizationController.isOptimalSharpePositive ? Theme.textPrimary : Theme.bearRed
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontLg
                                    font.weight: Font.Bold
                                }
                                Text {
                                    text: "Mevcut: " + optimizationController.currentSharpeFormatted
                                    color: Theme.textSecondary
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 10
                                }
                            }
                        }
                    }

                    // Kart 2: Beklenen Getiri
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 88
                        radius: Theme.radiusMd
                        color: Theme.bgCard
                        border.color: Theme.borderCard
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            anchors.topMargin: 10
                            anchors.bottomMargin: 10
                            spacing: Theme.spaceSm

                            Rectangle {
                                width: 36
                                height: 36
                                radius: Theme.radiusSm
                                color: optimizationController.isOptimalReturnPositive ? Theme.bullGreenSoft : Theme.bearRedSoft

                                ModernIcon {
                                    anchors.centerIn: parent
                                    name: optimizationController.isOptimalReturnPositive ? "trendingup" : "trendingdown"
                                    color: optimizationController.isOptimalReturnPositive ? Theme.bullGreen : Theme.bearRed
                                    size: 18
                                }
                            }

                            ColumnLayout {
                                spacing: 2
                                Text {
                                    text: Strings.optKpiExpReturn
                                    color: Theme.textMuted
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                }
                                Text {
                                    text: optimizationController.optimalReturnFormatted
                                    color: optimizationController.isOptimalReturnPositive ? Theme.bullGreen : Theme.bearRed
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontLg
                                    font.weight: Font.Bold
                                }
                                Text {
                                    text: "Mevcut: " + optimizationController.currentReturnFormatted
                                    color: optimizationController.isCurrentReturnPositive ? Theme.textSecondary : Theme.bearRed
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 10
                                }
                            }
                        }
                    }

                    // Kart 3: Yıllık Volatilite (Risk)
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 88
                        radius: Theme.radiusMd
                        color: Theme.bgCard
                        border.color: Theme.borderCard
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            anchors.topMargin: 10
                            anchors.bottomMargin: 10
                            spacing: Theme.spaceSm

                            Rectangle {
                                width: 36
                                height: 36
                                radius: Theme.radiusSm
                                color: Theme.warningYellowSoft

                                ModernIcon {
                                    anchors.centerIn: parent
                                    name: "shieldcheck"
                                    color: Theme.warningYellow
                                    size: 18
                                }
                            }

                            ColumnLayout {
                                spacing: 2
                                Text {
                                    text: Strings.optKpiVolatility
                                    color: Theme.textMuted
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                }
                                Text {
                                    text: optimizationController.optimalVolFormatted
                                    color: Theme.warningYellow
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontLg
                                    font.weight: Font.Bold
                                }
                                Text {
                                    text: "Mevcut: " + optimizationController.currentVolFormatted
                                    color: Theme.textSecondary
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 10
                                }
                            }
                        }
                    }

                    // Kart 4: Minimum Risk Portföyü
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 88
                        radius: Theme.radiusMd
                        color: Theme.bgCard
                        border.color: Theme.borderCard
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            anchors.topMargin: 10
                            anchors.bottomMargin: 10
                            spacing: Theme.spaceSm

                            Rectangle {
                                width: 36
                                height: 36
                                radius: Theme.radiusSm
                                color: Theme.accentSoft

                                ModernIcon {
                                    anchors.centerIn: parent
                                    name: "piechart"
                                    color: Theme.accent
                                    size: 18
                                }
                            }

                            ColumnLayout {
                                spacing: 2
                                Text {
                                    text: Strings.optKpiMinVol
                                    color: Theme.textMuted
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                }
                                Text {
                                    text: optimizationController.minVolFormatted
                                    color: Theme.accent
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontLg
                                    font.weight: Font.Bold
                                }
                                Text {
                                    text: "Minimum risk sınırı"
                                    color: Theme.textSecondary
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 10
                                }
                            }
                        }
                    }
                }

                // 2. SEKME ÇUBUĞU (3 SEKME)
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceSm

                    Row {
                        spacing: Theme.spaceXs

                        Repeater {
                            model: [
                                { idx: 0, text: Strings.optTabFrontier, icon: "crosshair" },
                                { idx: 1, text: Strings.optTabWeights, icon: "barchart" },
                                { idx: 2, text: Strings.optTabRebalance, icon: "layers" }
                            ]

                            Rectangle {
                                width: tabRow.width + 20
                                height: 34
                                radius: Theme.radiusSm
                                color: optimizationController.activeTab === modelData.idx ? Theme.accent : (tabMouse.containsMouse ? Theme.bgCardHover : Theme.bgSecondary)
                                border.color: optimizationController.activeTab === modelData.idx ? Theme.accent : Theme.borderSubtle
                                border.width: 1

                                RowLayout {
                                    id: tabRow
                                    anchors.centerIn: parent
                                    spacing: 6

                                    ModernIcon {
                                        name: modelData.icon
                                        color: optimizationController.activeTab === modelData.idx ? Theme.textInverse : Theme.textSecondary
                                        size: 13
                                    }

                                    Text {
                                        text: modelData.text
                                        color: optimizationController.activeTab === modelData.idx ? Theme.textInverse : Theme.textSecondary
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSm
                                        font.weight: optimizationController.activeTab === modelData.idx ? Font.DemiBold : Font.Normal
                                    }
                                }

                                MouseArea {
                                    id: tabMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: optimizationController.setActiveTab(modelData.idx)
                                }
                            }
                        }
                    }

                    Item { Layout.fillWidth: true }
                }

                // 3. İÇERİK KARTI (WebEngineView / Tablo)
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: Theme.radiusMd
                    color: Theme.bgCard
                    border.color: Theme.borderCard
                    border.width: 1
                    clip: true

                    // Yükleniyor Durumu
                    ColumnLayout {
                        anchors.centerIn: parent
                        visible: optimizationController.isLoading
                        spacing: Theme.spaceSm

                        BusyIndicator {
                            Layout.alignment: Qt.AlignHCenter
                            running: optimizationController.isLoading
                        }

                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: Strings.optCalculating
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                        }
                    }

                    // Henüz Çalıştırılmadı Boş Durumu
                    ColumnLayout {
                        anchors.centerIn: parent
                        visible: !optimizationController.hasResults && !optimizationController.isLoading
                        spacing: Theme.spaceSm

                        ModernIcon {
                            Layout.alignment: Qt.AlignHCenter
                            name: "optimization"
                            size: 48
                            color: Theme.textMuted
                        }

                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: Strings.optEmptyTitle
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBase
                            font.weight: Font.Bold
                        }

                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: Strings.optEmptySubtitle
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                        }
                    }

                    // SEKME 0: Verimli Sınır (Efficient Frontier) Saçılım Grafiği
                    WebEngineView {
                        id: frontierWebView
                        anchors.fill: parent
                        backgroundColor: Theme.bgCard
                        visible: optimizationController.hasResults && !optimizationController.isLoading && optimizationController.activeTab === 0
                        settings.javascriptEnabled: true
                        settings.localContentCanAccessRemoteUrls: true

                        Connections {
                            target: optimizationController
                            function onChartHtmlChanged() {
                                if (optimizationController.chartHtml !== "") {
                                    frontierWebView.loadHtml(optimizationController.chartHtml)
                                }
                            }
                        }

                        Component.onCompleted: {
                            if (optimizationController.chartHtml !== "") {
                                frontierWebView.loadHtml(optimizationController.chartHtml)
                            }
                        }
                    }

                    // SEKME 1: Ağırlık Karşılaştırması Çubuk Grafiği
                    WebEngineView {
                        id: weightsWebView
                        anchors.fill: parent
                        backgroundColor: Theme.bgCard
                        visible: optimizationController.hasResults && !optimizationController.isLoading && optimizationController.activeTab === 1
                        settings.javascriptEnabled: true
                        settings.localContentCanAccessRemoteUrls: true

                        Connections {
                            target: optimizationController
                            function onWeightsChartHtmlChanged() {
                                if (optimizationController.weightsChartHtml !== "") {
                                    weightsWebView.loadHtml(optimizationController.weightsChartHtml)
                                }
                            }
                        }

                        Component.onCompleted: {
                            if (optimizationController.weightsChartHtml !== "") {
                                weightsWebView.loadHtml(optimizationController.weightsChartHtml)
                            }
                        }
                    }

                    // SEKME 2: Yeniden Dengeleme (Rebalance) Öneri Tablosu
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: Theme.spaceMd
                        visible: optimizationController.hasResults && !optimizationController.isLoading && optimizationController.activeTab === 2
                        spacing: Theme.spaceSm

                        // Tablo Başlık Satırı
                        Rectangle {
                            Layout.fillWidth: true
                            height: 36
                            radius: Theme.radiusSm
                            color: Theme.bgSecondary

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: Theme.spaceMd
                                anchors.rightMargin: Theme.spaceMd
                                spacing: Theme.spaceSm

                                Text { Layout.preferredWidth: 80; text: Strings.optThSymbol; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.Bold }
                                Text { Layout.fillWidth: true; text: Strings.optThCompany; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.Bold }
                                Text { Layout.preferredWidth: 80; horizontalAlignment: Text.AlignRight; text: Strings.optThCurrentWeight; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.Bold }
                                Text { Layout.preferredWidth: 80; horizontalAlignment: Text.AlignRight; text: Strings.optThOptimalWeight; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.Bold }
                                Text { Layout.preferredWidth: 80; horizontalAlignment: Text.AlignRight; text: Strings.optThChange; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.Bold }
                                Text { Layout.preferredWidth: 100; horizontalAlignment: Text.AlignHCenter; text: Strings.optThAction; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.Bold }
                                Text { Layout.preferredWidth: 110; horizontalAlignment: Text.AlignRight; text: Strings.optThAmountDiff; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.Bold }
                                Text { Layout.preferredWidth: 70; horizontalAlignment: Text.AlignRight; text: Strings.optThEstShares; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.Bold }
                            }
                        }

                        // Tablo Satırları
                        ListView {
                            id: rebalanceList
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            spacing: 4
                            model: optimizationController.suggestions

                            ScrollBar.vertical: ModernScrollBar {}

                            delegate: Rectangle {
                                width: rebalanceList.width
                                height: 42
                                radius: Theme.radiusSm
                                color: rowMouse.containsMouse ? Theme.bgCardHover : Theme.bgSecondary
                                border.color: Theme.borderSubtle
                                border.width: 1

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: Theme.spaceMd
                                    anchors.rightMargin: Theme.spaceMd
                                    spacing: Theme.spaceSm

                                    // Sembol
                                    Text {
                                        Layout.preferredWidth: 80
                                        text: (modelData.symbol || "").replace(/\.IS$/i, "").replace(/\.IS/g, "")
                                        color: Theme.textPrimary
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSm
                                        font.weight: Font.Bold
                                    }

                                    // Şirket Adı
                                    Text {
                                        Layout.fillWidth: true
                                        text: {
                                            var cn = (modelData.companyName || modelData.symbol || "")
                                            return cn.replace(/\.IS$/i, "").replace(/\.IS/g, "")
                                        }
                                        color: Theme.textSecondary
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSm
                                        elide: Text.ElideRight
                                    }

                                    // Mevcut %
                                    Text {
                                        Layout.preferredWidth: 80
                                        horizontalAlignment: Text.AlignRight
                                        text: "%" + (modelData.currentWeight || 0).toFixed(2).replace('.', ',')
                                        color: Theme.textSecondary
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSm
                                    }

                                    // Optimum %
                                    Text {
                                        Layout.preferredWidth: 80
                                        horizontalAlignment: Text.AlignRight
                                        text: "%" + (modelData.optimalWeight || 0).toFixed(2).replace('.', ',')
                                        color: Theme.textPrimary
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSm
                                        font.weight: Font.DemiBold
                                    }

                                    // Fark %
                                    Text {
                                        Layout.preferredWidth: 80
                                        horizontalAlignment: Text.AlignRight
                                        text: {
                                            var ch = modelData.change || 0
                                            var str = Math.abs(ch).toFixed(2).replace('.', ',')
                                            if (ch > 0) return "+%" + str
                                            if (ch < 0) return "-%" + str
                                            return "%0,00"
                                        }
                                        color: modelData.change > 0 ? Theme.bullGreen : (modelData.change < 0 ? Theme.bearRed : Theme.textMuted)
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSm
                                        font.weight: Font.Bold
                                    }

                                    // Aksiyon Rozeti (EKLE / AZALT / TUT)
                                    Rectangle {
                                        Layout.preferredWidth: 100
                                        Layout.alignment: Qt.AlignHCenter
                                        height: 24
                                        radius: Theme.radiusXs
                                        color: modelData.action === "EKLE" ? Theme.bullGreenSoft : (modelData.action === "AZALT" ? Theme.bearRedSoft : Theme.bgSecondary)
                                        border.color: modelData.action === "EKLE" ? Theme.bullGreen : (modelData.action === "AZALT" ? Theme.bearRed : Theme.borderSubtle)
                                        border.width: 1

                                        Text {
                                            anchors.centerIn: parent
                                            text: modelData.action
                                            color: modelData.action === "EKLE" ? Theme.bullGreen : (modelData.action === "AZALT" ? Theme.bearRed : Theme.textMuted)
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.fontXs
                                            font.weight: Font.Bold
                                        }
                                    }

                                    // Tahmini Tutar Farkı (₺)
                                    Text {
                                        Layout.preferredWidth: 110
                                        horizontalAlignment: Text.AlignRight
                                        text: {
                                            var ad = modelData.amountDiff || 0
                                            var str = Math.abs(ad).toLocaleString(Qt.locale("tr_TR"), "f", 2) + " ₺"
                                            if (ad > 0) return "+" + str
                                            if (ad < 0) return "-" + str
                                            return "0,00 ₺"
                                        }
                                        color: modelData.amountDiff > 0 ? Theme.bullGreen : (modelData.amountDiff < 0 ? Theme.bearRed : Theme.textMuted)
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSm
                                        font.weight: Font.DemiBold
                                    }

                                    // Tahmini Lot
                                    Text {
                                        Layout.preferredWidth: 70
                                        horizontalAlignment: Text.AlignRight
                                        text: modelData.estShares > 0 ? modelData.estShares.toLocaleString(Qt.locale("tr_TR")) : "-"
                                        color: Theme.textSecondary
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSm
                                    }
                                }

                                MouseArea {
                                    id: rowMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    RiskQuestionnaireDialog {
        id: riskQuestionnaire
    }
}
