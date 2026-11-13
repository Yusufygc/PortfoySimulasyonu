import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Hisse 360 > Finansal Performans görünümü: çeyreklik grafik, DuPont, FCF ve bilanço/gelir/nakit tabloları.
ColumnLayout {
    id: root
    readonly property var ctrl: (typeof stock360Controller !== "undefined") ? stock360Controller : null
    property real hostWidth: 0
    width: root.hostWidth
    spacing: Theme.spaceMd

    // 1. Çeyreklik Gelir ve Kârlılık Gelişim Grafiği (Fintech Çift Eksen)
    FintechRevenueChart {
        Layout.fillWidth: true
    }

    // 2. Kârlılık Anatomisi (DuPont ROE) ve Serbest Nakit Akışı (FCF) Kartları
    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.spaceMd

        FintechDuPontCard {
            Layout.fillWidth: true
            Layout.preferredWidth: 550
            Layout.minimumWidth: 360
        }

        FintechCashFlowCard {
            Layout.fillWidth: true
            Layout.preferredWidth: 450
            Layout.minimumWidth: 320
        }
    }

    // 3. Profesyonel Fintech Tabloları (Bilanço, Gelir, Nakit Akış Tablosu)
    FintechStatementsTable {
        Layout.fillWidth: true
    }
}
