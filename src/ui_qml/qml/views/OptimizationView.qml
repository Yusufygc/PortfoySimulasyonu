import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import QtWebEngine
import "../theme"
import "../components"

Rectangle {
    id: root

    color: Theme.bgPrimary

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
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.spaceMd

            // SOL KONTROL PANELİ
            Rectangle {
                Layout.preferredWidth: 320
                Layout.minimumWidth: 280
                Layout.fillHeight: true
                radius: Theme.radiusMd
                color: Theme.bgCard
                border.color: Theme.borderCard
                border.width: 1

                ScrollView {
                    anchors.fill: parent
                    anchors.margins: Theme.spaceMd
                    clip: true
                    ScrollBar.vertical: ModernScrollBar {}

                    ColumnLayout {
                        width: parent.width
                        spacing: Theme.spaceMd

                        // Başlık
                        Text {
                            text: "OPTİMİZASYON PARAMETRELERİ"
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            font.weight: Font.DemiBold
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
                                Layout.preferredHeight: 36
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
                                    height: 32
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
                                Layout.preferredHeight: 36
                                model: optimizationController.riskProfileOptions
                                textRole: "label"

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
                                    height: 32
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
                                    width: weightValText.width + 12
                                    height: 22
                                    radius: Theme.radiusXs
                                    color: Theme.accentSoft

                                    Text {
                                        id: weightValText
                                        anchors.centerIn: parent
                                        text: "%" + Math.round(optimizationController.maxSingleWeight)
                                        color: Theme.accent
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontXs
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
                                    width: rfValText.width + 12
                                    height: 22
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
                                        font.pixelSize: Theme.fontXs
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
                            implicitHeight: infoCol.height + 16

                            ColumnLayout {
                                id: infoCol
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 4

                                RowLayout {
                                    spacing: 6
                                    ModernIcon {
                                        name: "info"
                                        size: 13
                                        color: Theme.accent
                                    }
                                    Text {
                                        text: "Modern Portföy Teorisi (MPT)"
                                        color: Theme.accent
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontXs
                                        font.weight: Font.DemiBold
                                    }
                                }

                                Text {
                                    Layout.fillWidth: true
                                    wrapMode: Text.WordWrap
                                    text: "Ledoit-Wolf kovaryans daraltması ve SciPy SLSQP çözücüsü ile portföyün risk başına getirisini (Sharpe) maksimize eder."
                                    color: Theme.textMuted
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 11
                                    lineHeight: 1.25
                                }
                            }
                        }

                        Item { Layout.fillHeight: true }

                        // Durum Mesajı
                        Text {
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            visible: optimizationController.statusMessage !== ""
                            text: optimizationController.statusMessage
                            color: optimizationController.hasResults ? Theme.success : Theme.warning
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                        }

                        // Çalıştır Butonu
                        Rectangle {
                            Layout.fillWidth: true
                            height: 42
                            radius: Theme.radiusSm
                            color: btnRunMouse.containsMouse ? Theme.accentHover : Theme.accent
                            opacity: optimizationController.isLoading ? 0.7 : 1.0

                            RowLayout {
                                anchors.centerIn: parent
                                spacing: Theme.spaceXs

                                ModernIcon {
                                    name: "refresh"
                                    color: Theme.textInverse
                                    size: 16
                                    visible: !optimizationController.isLoading
                                }

                                BusyIndicator {
                                    width: 18
                                    height: 18
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
                        }
                    }
                }
            }

            // SAĞ ANA ALAN (KPI + Sekmeler + Grafik / Tablo)
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: Theme.spaceMd

                // 1. KPI ŞERİDİ (4 KART)
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceMd

                    // Kart 1: Maksimum Sharpe
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 76
                        radius: Theme.radiusMd
                        color: Theme.bgCard
                        border.color: Theme.borderCard
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: Theme.spaceMd
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
                                    color: Theme.textPrimary
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
                        Layout.preferredHeight: 76
                        radius: Theme.radiusMd
                        color: Theme.bgCard
                        border.color: Theme.borderCard
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: Theme.spaceMd
                            spacing: Theme.spaceSm

                            Rectangle {
                                width: 36
                                height: 36
                                radius: Theme.radiusSm
                                color: Theme.successSoft

                                ModernIcon {
                                    anchors.centerIn: parent
                                    name: "trendingup"
                                    color: Theme.success
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
                                    color: Theme.success
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontLg
                                    font.weight: Font.Bold
                                }
                                Text {
                                    text: "Mevcut: " + optimizationController.currentReturnFormatted
                                    color: Theme.textSecondary
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 10
                                }
                            }
                        }
                    }

                    // Kart 3: Yıllık Volatilite (Risk)
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 76
                        radius: Theme.radiusMd
                        color: Theme.bgCard
                        border.color: Theme.borderCard
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: Theme.spaceMd
                            spacing: Theme.spaceSm

                            Rectangle {
                                width: 36
                                height: 36
                                radius: Theme.radiusSm
                                color: Theme.warningSoft

                                ModernIcon {
                                    anchors.centerIn: parent
                                    name: "shieldcheck"
                                    color: Theme.warning
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
                                    color: Theme.warning
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
                        Layout.preferredHeight: 76
                        radius: Theme.radiusMd
                        color: Theme.bgCard
                        border.color: Theme.borderCard
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: Theme.spaceMd
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
                                    text: "Minimun risk sınırı"
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
                                        text: modelData.symbol
                                        color: Theme.textPrimary
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSm
                                        font.weight: Font.Bold
                                    }

                                    // Şirket Adı
                                    Text {
                                        Layout.fillWidth: true
                                        text: modelData.companyName || modelData.symbol
                                        color: Theme.textSecondary
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSm
                                        elide: Text.ElideRight
                                    }

                                    // Mevcut %
                                    Text {
                                        Layout.preferredWidth: 80
                                        horizontalAlignment: Text.AlignRight
                                        text: "%" + modelData.currentWeight.toFixed(2)
                                        color: Theme.textSecondary
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSm
                                    }

                                    // Optimum %
                                    Text {
                                        Layout.preferredWidth: 80
                                        horizontalAlignment: Text.AlignRight
                                        text: "%" + modelData.optimalWeight.toFixed(2)
                                        color: Theme.textPrimary
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSm
                                        font.weight: Font.DemiBold
                                    }

                                    // Fark %
                                    Text {
                                        Layout.preferredWidth: 80
                                        horizontalAlignment: Text.AlignRight
                                        text: (modelData.change > 0 ? "+" : "") + modelData.change.toFixed(2) + "%"
                                        color: modelData.change > 0 ? Theme.success : (modelData.change < 0 ? Theme.danger : Theme.textMuted)
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSm
                                        font.weight: Font.Bold
                                    }

                                    // Aksiyon Rozeti (EKLE / AZALT / TUT)
                                    Rectangle {
                                        Layout.preferredWidth: 90
                                        Layout.alignment: Qt.AlignHCenter
                                        height: 24
                                        radius: Theme.radiusXs
                                        color: modelData.action === "EKLE" ? Theme.successSoft : (modelData.action === "AZALT" ? Theme.dangerSoft : Theme.bgPrimary)
                                        border.color: modelData.action === "EKLE" ? Theme.success : (modelData.action === "AZALT" ? Theme.danger : Theme.borderSubtle)
                                        border.width: 1

                                        Text {
                                            anchors.centerIn: parent
                                            text: modelData.action
                                            color: modelData.action === "EKLE" ? Theme.success : (modelData.action === "AZALT" ? Theme.danger : Theme.textMuted)
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.fontXs
                                            font.weight: Font.Bold
                                        }
                                    }

                                    // Tahmini Tutar Farkı (₺)
                                    Text {
                                        Layout.preferredWidth: 110
                                        horizontalAlignment: Text.AlignRight
                                        text: (modelData.amountDiff > 0 ? "+" : "") + modelData.amountDiff.toLocaleString(Qt.locale("tr_TR"), "f", 2) + " ₺"
                                        color: modelData.amountDiff > 0 ? Theme.success : (modelData.amountDiff < 0 ? Theme.danger : Theme.textMuted)
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
}
