import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    id: root

    Component.onCompleted: {
        portfolioController.refreshData()
    }

    // Toast Bildirim Durumu
    property string toastMessage: ""
    property bool toastSuccess: true
    property bool toastVisible: false

    Connections {
        target: portfolioController
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

    // Ana Düzen (Sol Panel + Sağ Detay Paneli)
    RowLayout {
        anchors.fill: parent
        spacing: Theme.spaceMd

        // Sol Panel: Portföy Listesi (280px)
        PortfolioListCard {
            id: listCard
            Layout.preferredWidth: 280
            Layout.minimumWidth: 240
            Layout.maximumWidth: 320
            Layout.fillHeight: true

            onNewPortfolioRequested: {
                newPortfolioDialog.isEdit = false
                newPortfolioDialog.open()
            }

            onEditPortfolioRequested: function(pId, name, desc) {
                newPortfolioDialog.isEdit = true
                newPortfolioDialog.editPortfolioId = pId
                newPortfolioDialog.editName = name
                newPortfolioDialog.editDesc = desc
                newPortfolioDialog.open()
            }
        }

        // Sağ Panel: Seçili Portföy Detayı & Pozisyonlar
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "transparent"

            // 1. Portföy Seçili Olmadığında Boş Durum
            ColumnLayout {
                anchors.centerIn: parent
                visible: portfolioController.currentPortfolioId <= 0
                spacing: Theme.spaceMd

                ModernIcon {
                    Layout.alignment: Qt.AlignHCenter
                    iconSource: Icons.get("portfolio")
                    iconColor: Theme.textMuted
                    width: 48
                    height: 48
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: Strings.portfolioSelectOne
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXl
                    font.weight: Font.DemiBold
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: Strings.portfolioSelectOneDesc
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                }
            }

            // 2. Portföy Seçiliyken Gösterilen İçerik
            ColumnLayout {
                anchors.fill: parent
                spacing: Theme.spaceMd
                visible: portfolioController.currentPortfolioId > 0

                // Başlık & Hızlı Aksiyon Butonları
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceMd

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        Text {
                            text: portfolioController.currentPortfolioName
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXl
                            font.weight: Font.Bold
                        }

                        Text {
                            text: portfolioController.currentPortfolioDesc || Strings.portfolioSubtitle
                            color: Theme.textSecondary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                    }

                    // Aksiyon Butonları
                    RowLayout {
                        spacing: Theme.spaceSm

                        // Fiyatları Güncelle Butonu
                        Rectangle {
                            height: 36
                            width: btnRefreshRow.width + Theme.spaceMd * 2
                            radius: Theme.radiusSm
                            color: btnRefreshMouse.containsMouse ? Theme.bgCardHover : Theme.bgCard
                            border.color: Theme.borderSubtle
                            border.width: 1

                            RowLayout {
                                id: btnRefreshRow
                                anchors.centerIn: parent
                                spacing: Theme.spaceXs

                                ModernIcon {
                                    iconSource: Icons.get("refresh")
                                    iconColor: Theme.textSecondary
                                    width: 14
                                    height: 14
                                }

                                Text {
                                    text: Strings.portfolioBtnRefreshPrices
                                    color: Theme.textSecondary
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSm
                                    font.weight: Font.DemiBold
                                }
                            }

                            MouseArea {
                                id: btnRefreshMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: portfolioController.refreshPrices()
                            }
                        }

                        // Sermaye Yönetimi Butonu
                        Rectangle {
                            height: 36
                            width: btnCapitalRow.width + Theme.spaceMd * 2
                            radius: Theme.radiusSm
                            color: btnCapitalMouse.containsMouse ? Theme.bgCardHover : Theme.bgCard
                            border.color: Theme.borderSubtle
                            border.width: 1

                            RowLayout {
                                id: btnCapitalRow
                                anchors.centerIn: parent
                                spacing: Theme.spaceXs

                                ModernIcon {
                                    iconSource: Icons.get("capital")
                                    iconColor: Theme.textSecondary
                                    width: 14
                                    height: 14
                                }

                                Text {
                                    text: Strings.portfolioBtnCapital
                                    color: Theme.textSecondary
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSm
                                    font.weight: Font.DemiBold
                                }
                            }

                            MouseArea {
                                id: btnCapitalMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: capitalMovementDialog.open()
                            }
                        }

                        // Excel Raporu Butonu
                        Rectangle {
                            height: 36
                            width: btnExcelRow.width + Theme.spaceMd * 2
                            radius: Theme.radiusSm
                            color: btnExcelMouse.containsMouse ? Theme.bgCardHover : Theme.bgCard
                            border.color: Theme.borderSubtle
                            border.width: 1

                            RowLayout {
                                id: btnExcelRow
                                anchors.centerIn: parent
                                spacing: Theme.spaceXs

                                ModernIcon {
                                    iconSource: Icons.get("filetext")
                                    iconColor: Theme.textSecondary
                                    width: 14
                                    height: 14
                                }

                                Text {
                                    text: Strings.btnExportExcel
                                    color: Theme.textSecondary
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSm
                                    font.weight: Font.DemiBold
                                }
                            }

                            MouseArea {
                                id: btnExcelMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    if (typeof portfolioController !== "undefined") {
                                        portfolioController.exportToExcel()
                                    }
                                }
                            }
                        }

                        // Yeni İşlem Butonu (+ Primary)
                        Rectangle {
                            height: 36
                            width: btnTradeRow.width + Theme.spaceMd * 2
                            radius: Theme.radiusSm
                            color: btnTradeMouse.containsMouse ? Theme.accentHover : Theme.accent

                            RowLayout {
                                id: btnTradeRow
                                anchors.centerIn: parent
                                spacing: Theme.spaceXs

                                ModernIcon {
                                    iconSource: Icons.get("plus")
                                    iconColor: Theme.textInverse
                                    width: 14
                                    height: 14
                                }

                                Text {
                                    text: Strings.portfolioBtnNewTrade
                                    color: Theme.textInverse
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSm
                                    font.weight: Font.DemiBold
                                }
                            }

                            MouseArea {
                                id: btnTradeMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: newTradeDialog.open()
                            }
                        }
                    }
                }

                // KPI Özet Şeridi
                PortfolioSummaryStrip {
                    Layout.fillWidth: true
                }

                // Pozisyonlar Tablosu (Pozisyon Varsa)
                PortfolioPositionsTable {
                    id: positionsTable
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    visible: portfolioController.hasPositions

                    onPositionClicked: function(stockId, ticker) {
                        if (typeof stockDetailController !== "undefined") {
                            stockDetailController.openStockWithContext(ticker, "model", portfolioController.currentPortfolioId)
                        }
                    }
                }

                // Pozisyon Yokken Boş Durum Kartı
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: Theme.bgCard
                    radius: Theme.radiusMd
                    border.color: Theme.borderCard
                    border.width: 1
                    visible: !portfolioController.hasPositions

                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: Theme.spaceSm

                        ModernIcon {
                            Layout.alignment: Qt.AlignHCenter
                            iconSource: Icons.get("trendingup")
                            iconColor: Theme.textMuted
                            width: 42
                            height: 42
                        }

                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: Strings.portfolioEmptyTitle
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontLg
                            font.weight: Font.DemiBold
                        }

                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: Strings.portfolioEmptySubtitle
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                        }

                        Item { height: Theme.spaceSm }

                        Rectangle {
                            Layout.alignment: Qt.AlignHCenter
                            width: 140
                            height: 36
                            radius: Theme.radiusSm
                            color: btnEmptyTradeMouse.containsMouse ? Theme.accentHover : Theme.accent

                            RowLayout {
                                anchors.centerIn: parent
                                spacing: Theme.spaceXs

                                ModernIcon {
                                    iconSource: Icons.get("plus")
                                    iconColor: Theme.textInverse
                                    width: 14
                                    height: 14
                                }

                                Text {
                                    text: Strings.portfolioEmptyBtnTrade
                                    color: Theme.textInverse
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSm
                                    font.weight: Font.DemiBold
                                }
                            }

                            MouseArea {
                                id: btnEmptyTradeMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: newTradeDialog.open()
                            }
                        }
                    }
                }
            }
        }
    }

    // Toast Bildirim Kartı (Sağ Üst / Orta Üst)
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
                iconSource: Icons.get(root.toastSuccess ? "check" : "alert")
                iconColor: root.toastSuccess ? Theme.bullGreen : Theme.bearRed
                width: 16
                height: 16
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
    NewPortfolioDialog {
        id: newPortfolioDialog
    }

    NewTradeDialog {
        id: newTradeDialog
    }

    CapitalMovementDialog {
        id: capitalMovementDialog
    }
}
