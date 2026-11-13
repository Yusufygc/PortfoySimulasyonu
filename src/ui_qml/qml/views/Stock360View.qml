import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    id: root

    readonly property var ctrl: (typeof stock360Controller !== "undefined") ? stock360Controller : null

    Connections {
        target: root.ctrl
        function onViewModeChanged() {
            if (mainScrollView && mainScrollView.contentItem) {
                mainScrollView.contentItem.contentY = 0;
            }
        }
    }

    Component.onCompleted: {
        if (root.ctrl && typeof root.ctrl.ensureLoaded === "function") {
            root.ctrl.ensureLoaded();
        }
    }

    ScrollView {
        id: mainScrollView
        anchors.fill: parent
        clip: true
        contentHeight: mainColumn.childrenRect.height + Theme.spaceMd * 2
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

        ScrollBar.vertical: ModernScrollBar {
            parent: mainScrollView
            x: mainScrollView.mirrored ? 2 : mainScrollView.width - width - 3
            y: mainScrollView.topPadding + 2
            height: mainScrollView.availableHeight - 4
            active: mainScrollView.ScrollBar.vertical.active
        }

        ColumnLayout {
            id: mainColumn
            objectName: "mainColumn"
            width: mainScrollView.availableWidth
            spacing: Theme.spaceMd

            // ---------------------------------------------------------
            // 1. ÜST ARAÇ ÇUBUĞU & ARAMA & HIZLI HİSSE BUTONLARI
            // ---------------------------------------------------------
            Stock360TopBar {
                Layout.fillWidth: true
            }

            // ---------------------------------------------------------
            // 2. GÖRÜNÜM MODU SEÇİCİ SEKME BARI
            // ---------------------------------------------------------
            Stock360ModeTabs {
                Layout.fillWidth: true
            }

            // ---------------------------------------------------------
            // 3. ŞİRKET BİLGİ & FİYAT HERO KARTI (HER MODDA GÖRÜNÜR)
            // ---------------------------------------------------------
            Stock360HeroCard {
                Layout.fillWidth: true
            }

            // =========================================================
            // DİNAMİK GÖRÜNÜM MODU LOADER (0: Genel Bakış, 1: Bilanço, 2: KAP)
            // =========================================================
            Loader {
                id: viewModeLoader
                objectName: "viewModeLoader"
                Layout.fillWidth: true
                height: item ? item.implicitHeight : 0
                Layout.preferredHeight: height
                sourceComponent: {
                    var m = (root.ctrl) ? root.ctrl.viewMode : 0;
                    if (m === 1) return financialsComponent;
                    if (m === 2) return shareholdersComponent;
                    return overviewComponent;
                }
            }
        } // mainColumn sonu
    } // mainScrollView sonu

    // =========================================================
    // GÖRÜNÜM MODU 0: GENEL BAKIŞ & ÖZET KARTLAR
    // =========================================================
    Component {
        id: overviewComponent

        Stock360OverviewSection {
            hostWidth: viewModeLoader.width
        }
    }

    // =========================================================
    // GÖRÜNÜM MODU 1: FİNANSAL PERFORMANS & KAPSAMLI BİLANÇO
    // =========================================================
    Component {
        id: financialsComponent

        Stock360FinancialsSection {
            hostWidth: viewModeLoader.width
        }
    }

    // =========================================================
    // GÖRÜNÜM MODU 2: KAP ORTAKLIK TARİHÇESİ VE ZAMAN ÇİZELGESİ
    // =========================================================
    Component {
        id: shareholdersComponent

        Stock360ShareholdersSection {
            hostWidth: viewModeLoader.width
        }
    }
}


