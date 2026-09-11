import QtQuick
import QtQuick.Controls

// WatchlistView (bkz. plan §9.5) — birden fazla liste, hızlı ekle/çıkar,
// fiyat/günlük % kolonu. Veri: context property `watchlistController`
// (bkz. src/ui_qml/controllers/watchlist_controller.py).
Item {
    id: root
    anchors.fill: parent

    readonly property color colorProfit: "#10B981"
    readonly property color colorLoss: "#EF4444"
    function pctColor(value) { return value >= 0 ? colorProfit : colorLoss }
    function fmtPct(value) { return (value >= 0 ? "+" : "") + value.toFixed(2) + "%" }

    Column {
        id: headerColumn
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 20
        spacing: 10

        Row {
            spacing: 8

            Repeater {
                model: watchlistController.watchlistIds.length
                delegate: Button {
                    text: watchlistController.watchlistNames[index]
                    checkable: true
                    checked: watchlistController.activeWatchlistId === watchlistController.watchlistIds[index]
                    onClicked: watchlistController.selectWatchlist(watchlistController.watchlistIds[index])
                }
            }

            Rectangle {
                width: 160
                height: 36
                radius: 8
                color: "#151D2C"
                border.color: "#26354A"
                border.width: 1

                TextField {
                    id: newListField
                    anchors.fill: parent
                    anchors.margins: 4
                    placeholderText: "Yeni liste adı"
                    color: "#E5E7EB"
                    background: null
                    onAccepted: {
                        watchlistController.createWatchlist(text)
                        text = ""
                    }
                }
            }
        }

        Row {
            visible: watchlistController.activeWatchlistId !== -1
            spacing: 8

            Rectangle {
                width: 160
                height: 36
                radius: 8
                color: "#151D2C"
                border.color: "#26354A"
                border.width: 1

                TextField {
                    id: addTickerField
                    anchors.fill: parent
                    anchors.margins: 4
                    placeholderText: "Hisse ekle (örn. THYAO)"
                    color: "#E5E7EB"
                    background: null
                    onAccepted: {
                        watchlistController.addTicker(text)
                        text = ""
                    }
                }
            }

            Button { text: "Listeyi Sil"; onClicked: watchlistController.deleteActiveWatchlist() }
        }

        Text {
            visible: watchlistController.error !== ""
            text: watchlistController.error
            color: root.colorLoss
        }
    }

    Item {
        id: itemsArea
        objectName: "itemsArea"
        anchors.top: headerColumn.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.topMargin: 14
        anchors.leftMargin: 20
        anchors.rightMargin: 20
        anchors.bottomMargin: 20

        Rectangle {
            anchors.fill: parent
            radius: 12
            color: "#151D2C"
            border.color: "#26354A"
            border.width: 1

            Flickable {
                anchors.fill: parent
                anchors.margins: 8
                contentHeight: itemsColumn.height
                clip: true

                Column {
                    id: itemsColumn
                    width: parent.width
                    spacing: 1

                    Repeater {
                        model: watchlistController.itemTickers.length
                        delegate: Rectangle {
                            width: itemsColumn.width
                            height: 36
                            color: "transparent"

                            Row {
                                anchors.fill: parent
                                anchors.leftMargin: 8
                                spacing: 14

                                Text { width: 80; anchors.verticalCenter: parent.verticalCenter; text: watchlistController.itemTickers[index]; color: "#E5E7EB"; font.bold: true }
                                Text { width: 220; anchors.verticalCenter: parent.verticalCenter; text: watchlistController.itemNames[index]; color: "#9CA3AF"; elide: Text.ElideRight }
                                Text { width: 90; anchors.verticalCenter: parent.verticalCenter; text: watchlistController.itemPrices[index].toFixed(2); color: "#E5E7EB" }
                                Text {
                                    width: 90; anchors.verticalCenter: parent.verticalCenter
                                    text: root.fmtPct(watchlistController.itemDailyChangePct[index])
                                    color: root.pctColor(watchlistController.itemDailyChangePct[index])
                                }
                                Button {
                                    text: "Çıkar"
                                    anchors.verticalCenter: parent.verticalCenter
                                    onClicked: watchlistController.removeTicker(watchlistController.itemTickers[index])
                                }
                            }
                        }
                    }

                    Text {
                        visible: watchlistController.itemTickers.length === 0
                        text: watchlistController.activeWatchlistId === -1
                            ? "Önce bir liste oluşturun."
                            : "Bu liste boş — yukarıdan hisse ekleyin."
                        color: "#9CA3AF"
                        leftPadding: 8
                        topPadding: 12
                    }
                }
            }
        }
    }
}
