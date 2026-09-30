import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    id: root

    ScrollView {
        id: mainScrollView
        anchors.fill: parent
        clip: true
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

        ScrollBar.vertical: ModernScrollBar {
            parent: mainScrollView
            x: mainScrollView.mirrored ? 2 : mainScrollView.width - width - 3
            y: mainScrollView.topPadding + 2
            height: mainScrollView.availableHeight - 4
            active: mainScrollView.ScrollBar.vertical.active
        }

        ColumnLayout {
            width: mainScrollView.availableWidth
            spacing: Theme.spaceMd

            // 1. Üst Başlık ve Aksiyon Butonları
            RowLayout {
                Layout.fillWidth: true

                Column {
                    spacing: 2
                    Text {
                        text: Strings.watchlistTitle
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXl
                        font.weight: Font.Bold
                        color: Theme.textPrimary
                    }
                    Text {
                        text: Strings.watchlistSubtitle
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        color: Theme.textMuted
                    }
                }

                Item { Layout.fillWidth: true }

                // Fiyatları Yenile Butonu
                ModernButton {
                    text: watchlistController && watchlistController.isRefreshing ? Strings.btnRefreshing : Strings.btnRefresh
                    iconName: "refresh"
                    variant: "secondary"
                    enabled: !(watchlistController && watchlistController.isRefreshing)
                    onClicked: {
                        if (watchlistController) watchlistController.refreshPrices()
                    }
                }

                // Yeni Liste Oluştur Butonu
                ModernButton {
                    text: Strings.btnNewWatchlist
                    iconName: "plus"
                    variant: "primary"
                    onClicked: manageModal.openCreate()
                }
            }

            // 2. KPI Özet Metrik Kartları
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceMd

                MetricCard {
                    Layout.fillWidth: true
                    title: Strings.kpiActiveList
                    value: (watchlistController && watchlistController.currentWatchlistName) ? watchlistController.currentWatchlistName : "-"
                    subText: (watchlistController ? watchlistController.currentWatchlistCount : 0) + " Takip Edilen Hisse"
                    iconName: "list"
                    isPositive: true
                }

                MetricCard {
                    Layout.fillWidth: true
                    title: Strings.kpiGainersLosers
                    value: (watchlistController ? (watchlistController.summaryGainersCount + " Yükselen / " + watchlistController.summaryLosersCount + " Düşen") : "-")
                    isPositive: watchlistController ? (watchlistController.summaryGainersCount >= watchlistController.summaryLosersCount) : true
                    subText: "Aktif Liste Dağılımı"
                    iconName: "trendingup"
                }

                MetricCard {
                    Layout.fillWidth: true
                    title: Strings.kpiAvgChange
                    value: (watchlistController && watchlistController.summaryAvgChange) ? watchlistController.summaryAvgChange : "%0.00"
                    isPositive: (watchlistController && watchlistController.summaryAvgChange.indexOf("+") !== -1)
                    subText: "Eşit Ağırlıklı Ortalama"
                    iconName: "linechart"
                }
            }

            // 3. Ana İçerik: Sol Liste Seçici & Sağ Hisse Tablosu
            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.max(520, stocksColumn.implicitHeight + 40)
                spacing: Theme.spaceMd

                // Sol Panel: Takip Listelerim (Watchlist Selector)
                ModernCard {
                    Layout.preferredWidth: 280
                    Layout.fillHeight: true

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: Theme.spaceMd
                        spacing: Theme.spaceSm

                        RowLayout {
                            Layout.fillWidth: true
                            ModernIcon {
                                name: "bookmark"
                                size: 15
                                color: Theme.accent
                            }
                            Text {
                                text: Strings.watchlistMyLists
                                font.family: Theme.fontFamily
                                font.pixelSize: 11
                                font.weight: Font.Bold
                                color: Theme.textMuted
                                Layout.fillWidth: true
                            }
                            Text {
                                text: (watchlistController && watchlistController.watchlists) ? (watchlistController.watchlists.length + " Liste") : ""
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                color: Theme.textMuted
                            }
                        }

                        // Listeler Listesi (ListView)
                        ListView {
                            id: watchlistsListView
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            spacing: 6
                            model: watchlistController ? watchlistController.watchlists : []

                            delegate: Rectangle {
                                id: wlRow
                                width: watchlistsListView.width
                                height: 48
                                radius: Theme.radiusSm

                                readonly property bool isSelected: watchlistController && (modelData.id === watchlistController.currentWatchlistId)
                                color: isSelected ? Theme.bgCardHover : (wlMouse.containsMouse ? Theme.bgInput : "transparent")
                                border.color: isSelected ? Theme.accent : "transparent"
                                border.width: isSelected ? 1 : 0

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 10
                                    anchors.rightMargin: 8
                                    spacing: 8

                                    Column {
                                        Layout.fillWidth: true
                                        spacing: 2
                                        Text {
                                            text: modelData.name
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.fontSm
                                            font.weight: wlRow.isSelected ? Font.Bold : Font.DemiBold
                                            color: wlRow.isSelected ? Theme.textPrimary : Theme.textSecondary
                                            elide: Text.ElideRight
                                            width: 150
                                        }
                                        Text {
                                            text: (modelData.description && modelData.description !== "") ? modelData.description : (modelData.count + " Hisse")
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.fontXs
                                            color: Theme.textMuted
                                            elide: Text.ElideRight
                                            width: 150
                                        }
                                    }

                                    // Hisse Adedi Rozeti
                                    Rectangle {
                                        implicitWidth: countText.implicitWidth + 12
                                        implicitHeight: 20
                                        radius: 10
                                        color: wlRow.isSelected ? Theme.accent : Theme.bgInput

                                        Text {
                                            id: countText
                                            anchors.centerIn: parent
                                            text: modelData.count
                                            font.family: Theme.monoFontFamily
                                            font.pixelSize: 10
                                            font.weight: Font.Bold
                                            color: wlRow.isSelected ? "#ffffff" : Theme.textMuted
                                        }
                                    }

                                    // Düzenle İkon Butonu
                                    Item {
                                        width: 22
                                        height: 22
                                        visible: wlMouse.containsMouse || wlRow.isSelected

                                        ModernIcon {
                                            name: "pencil"
                                            size: 13
                                            color: Theme.textMuted
                                            anchors.centerIn: parent
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: manageModal.openEdit(modelData.id, modelData.name, modelData.description)
                                        }
                                    }

                                    // Sil İkon Butonu
                                    Item {
                                        width: 22
                                        height: 22
                                        visible: wlMouse.containsMouse || wlRow.isSelected

                                        ModernIcon {
                                            name: "trash-2"
                                            size: 13
                                            color: Theme.bearRed
                                            anchors.centerIn: parent
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                if (watchlistController) watchlistController.deleteWatchlist(modelData.id)
                                            }
                                        }
                                    }
                                }

                                MouseArea {
                                    id: wlMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (watchlistController) watchlistController.selectWatchlist(modelData.id)
                                    }
                                }
                            }
                        }

                        // Alt Yeni Liste Butonu
                        ModernButton {
                            Layout.fillWidth: true
                            text: Strings.btnNewWatchlist
                            iconName: "plus"
                            variant: "secondary"
                            onClicked: manageModal.openCreate()
                        }
                    }
                }

                // Sağ Panel: Seçili Liste Hisseleri Tablosu
                ModernCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    ColumnLayout {
                        id: stocksColumn
                        anchors.fill: parent
                        anchors.margins: Theme.spaceMd
                        spacing: Theme.spaceSm

                        // Liste Başlığı & Hisse Ekle Butonu
                        RowLayout {
                            Layout.fillWidth: true

                            Column {
                                Layout.fillWidth: true
                                spacing: 2
                                Text {
                                    text: (watchlistController && watchlistController.currentWatchlistName !== "") ? watchlistController.currentWatchlistName : Strings.watchlistTitle
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontMd
                                    font.weight: Font.Bold
                                    color: Theme.textPrimary
                                }
                                Text {
                                    text: (watchlistController && watchlistController.currentWatchlistDesc !== "") ? watchlistController.currentWatchlistDesc : "Takip listesindeki hisselerin anlık piyasa fiyatları ve trendleri"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSm
                                    color: Theme.textMuted
                                }
                            }

                            ModernButton {
                                text: Strings.btnAddStockToWatchlist
                                iconName: "plus"
                                variant: "primary"
                                enabled: watchlistController && (watchlistController.currentWatchlistId > 0)
                                onClicked: addStockModal.open(watchlistController.currentWatchlistId)
                            }
                        }

                        // Tablo Başlık Satırı
                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 34
                            radius: Theme.radiusSm
                            color: Theme.bgInput

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 12
                                anchors.rightMargin: 12

                                Text { text: Strings.thSymbolCompany; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 160 }
                                Text { text: Strings.thLastPrice; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 85; horizontalAlignment: Text.AlignRight }
                                Text { text: Strings.thDailyChange; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 80; horizontalAlignment: Text.AlignRight }
                                Text { text: Strings.thDayRange; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 115; horizontalAlignment: Text.AlignHCenter }
                                Text { text: Strings.thTrend7D; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 85; horizontalAlignment: Text.AlignHCenter }
                                Text { text: Strings.thNotes; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.fillWidth: true }
                                Text { text: Strings.thActions; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 165; horizontalAlignment: Text.AlignRight }
                            }
                        }

                        // Dinamik Hisse Satırları (ListView)
                        ListView {
                            id: stocksListView
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            model: watchlistController ? watchlistController.stocksModel : null
                            visible: count > 0

                            delegate: Rectangle {
                                id: stockRow
                                width: stocksListView.width
                                height: 44
                                radius: Theme.radiusSm
                                color: stockMouse.containsMouse ? Theme.bgCardHover : "transparent"

                                Behavior on color { ColorAnimation { duration: 150 } }

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 12
                                    anchors.rightMargin: 12

                                    // 1. Sembol & Şirket
                                    Column {
                                        Layout.preferredWidth: 160
                                        spacing: 2
                                        Row {
                                            spacing: 6
                                            Text {
                                                text: model.cleanTicker
                                                font.family: Theme.monoFontFamily
                                                font.pixelSize: Theme.fontBase
                                                font.weight: Font.Bold
                                                color: Theme.textPrimary
                                            }
                                            Rectangle {
                                                width: 24
                                                height: 14
                                                radius: 3
                                                color: Theme.bgInput
                                                anchors.verticalCenter: parent.verticalCenter
                                                Text {
                                                    anchors.centerIn: parent
                                                    text: "BIST"
                                                    font.pixelSize: 8
                                                    font.weight: Font.Bold
                                                    color: Theme.textMuted
                                                }
                                            }
                                        }
                                        Text {
                                            text: model.companyName
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.fontXs
                                            color: Theme.textMuted
                                            elide: Text.ElideRight
                                            width: 150
                                        }
                                    }

                                    // 2. Son Fiyat
                                    Text {
                                        text: model.price
                                        font.family: Theme.monoFontFamily
                                        font.pixelSize: Theme.fontSm
                                        font.weight: Font.Bold
                                        color: Theme.textPrimary
                                        Layout.preferredWidth: 85
                                        horizontalAlignment: Text.AlignRight
                                    }

                                    // 3. Günlük Fark %
                                    Text {
                                        text: model.dailyDiff
                                        font.family: Theme.monoFontFamily
                                        font.pixelSize: Theme.fontSm
                                        font.weight: Font.DemiBold
                                        color: model.isUp ? Theme.bullGreen : Theme.bearRed
                                        Layout.preferredWidth: 80
                                        horizontalAlignment: Text.AlignRight
                                    }

                                    // 4. Gün İçi Aralık (Low - High Mini Bar)
                                    ColumnLayout {
                                        Layout.preferredWidth: 115
                                        spacing: 2
                                        Layout.alignment: Qt.AlignVCenter

                                        RowLayout {
                                            Layout.fillWidth: true
                                            Text { text: model.dayLow; font.pixelSize: 9; color: Theme.textMuted }
                                            Item { Layout.fillWidth: true }
                                            Text { text: model.dayHigh; font.pixelSize: 9; color: Theme.textMuted }
                                        }

                                        Rectangle {
                                            Layout.fillWidth: true
                                            implicitHeight: 4
                                            radius: 2
                                            color: Theme.bgInput

                                            Rectangle {
                                                width: 8
                                                height: 8
                                                radius: 4
                                                y: -2
                                                x: Math.max(0, Math.min(parent.width - 8, parent.width * model.dayRangePct - 4))
                                                color: model.isUp ? Theme.bullGreen : Theme.bearRed
                                            }
                                        }
                                    }

                                    // 5. 7G Trend Mini Sparkline
                                    MiniSparkline {
                                        Layout.preferredWidth: 85
                                        Layout.preferredHeight: 24
                                        Layout.alignment: Qt.AlignVCenter
                                        points: model.sparkline
                                        isUp: model.isUp
                                    }

                                    // 6. Notlar & Strateji
                                    Text {
                                        text: model.notes !== "" ? model.notes : "-"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontXs
                                        color: model.notes !== "" ? Theme.textSecondary : Theme.textMuted
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }

                                    // 7. Aksiyonlar (Grafik, İşlem, Not Düzenle, Sil)
                                    RowLayout {
                                        Layout.preferredWidth: 165
                                        spacing: 4
                                        Layout.alignment: Qt.AlignRight

                                        ModernButton {
                                            text: Strings.btnChart
                                            variant: "ghost"
                                            implicitHeight: 26
                                            implicitWidth: 55
                                            onClicked: {
                                                if (chartController) chartController.loadStock(model.ticker)
                                                if (shellController) shellController.navigateTo(0)
                                            }
                                        }

                                        ModernButton {
                                            text: Strings.btnTrade
                                            variant: "secondary"
                                            implicitHeight: 26
                                            implicitWidth: 50
                                            onClicked: {
                                                tradeModal.open(model.ticker, model.priceRaw)
                                            }
                                        }

                                        // Not Düzenle İkonu
                                        Item {
                                            width: 24
                                            height: 24
                                            ModernIcon {
                                                name: "pencil"
                                                size: 13
                                                color: Theme.textMuted
                                                anchors.centerIn: parent
                                            }
                                            MouseArea {
                                                anchors.fill: parent
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: editNoteModal.open(watchlistController.currentWatchlistId, model.stockId, model.cleanTicker, model.notes)
                                            }
                                        }

                                        // Listeden Kaldır İkonu
                                        Item {
                                            width: 24
                                            height: 24
                                            ModernIcon {
                                                name: "trash-2"
                                                size: 13
                                                color: Theme.bearRed
                                                anchors.centerIn: parent
                                            }
                                            MouseArea {
                                                anchors.fill: parent
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: {
                                                    if (watchlistController) watchlistController.removeStock(watchlistController.currentWatchlistId, model.stockId)
                                                }
                                            }
                                        }
                                    }
                                }

                                MouseArea {
                                    id: stockMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (chartController) chartController.loadStock(model.ticker)
                                    }
                                }
                            }
                        }

                        // Boş Liste Durumu (Empty State)
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            visible: stocksListView.count === 0
                            color: "transparent"

                            ColumnLayout {
                                anchors.centerIn: parent
                                spacing: Theme.spaceSm

                                ModernIcon {
                                    name: "star"
                                    size: 36
                                    color: Theme.textMuted
                                    Layout.alignment: Qt.AlignHCenter
                                }

                                Text {
                                    text: Strings.emptyWatchlistTitle
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontBase
                                    font.weight: Font.Bold
                                    color: Theme.textPrimary
                                    Layout.alignment: Qt.AlignHCenter
                                }

                                Text {
                                    text: Strings.emptyWatchlistSubtitle
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSm
                                    color: Theme.textMuted
                                    Layout.alignment: Qt.AlignHCenter
                                }

                                Item { height: 6 }

                                ModernButton {
                                    text: Strings.btnAddStockToWatchlist
                                    iconName: "plus"
                                    variant: "primary"
                                    Layout.alignment: Qt.AlignHCenter
                                    enabled: watchlistController && (watchlistController.currentWatchlistId > 0)
                                    onClicked: addStockModal.open(watchlistController.currentWatchlistId)
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // --- Modallar & Bildirimler ---

    AddStockModal {
        id: addStockModal
    }

    ManageWatchlistModal {
        id: manageModal
    }

    EditStockNoteModal {
        id: editNoteModal
    }

    QuickTradeModal {
        id: tradeModal
    }

    ToastNotification {
        id: toast
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        anchors.margins: Theme.spaceLg
    }

    // Python WatchlistController Sinyal Bağlantısı
    Connections {
        target: watchlistController

        function onActionCompleted(success, message) {
            toast.show(message, success)
        }
    }
}
