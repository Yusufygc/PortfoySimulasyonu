pragma Singleton
import QtQuick

QtObject {
    id: root

    // --- Menü & Sayfa İkonları ---
    readonly property url dashboard:     Qt.resolvedUrl("../../assets/icons/layout-dashboard.svg")
    readonly property url watchlist:     Qt.resolvedUrl("../../assets/icons/star.svg")
    readonly property url portfolio:     Qt.resolvedUrl("../../assets/icons/wallet.svg")
    readonly property url stock360:      Qt.resolvedUrl("../../assets/icons/target.svg")
    readonly property url compare:       Qt.resolvedUrl("../../assets/icons/scale.svg")
    readonly property url screener:      Qt.resolvedUrl("../../assets/icons/search.svg")
    readonly property url planning:      Qt.resolvedUrl("../../assets/icons/calendar.svg")
    readonly property url optimization:  Qt.resolvedUrl("../../assets/icons/shield-check.svg")
    readonly property url ai:            Qt.resolvedUrl("../../assets/icons/bot.svg")
    readonly property url settings:      Qt.resolvedUrl("../../assets/icons/settings.svg")

    // --- Aksiyon & Araç İkonları ---
    readonly property url refresh:       Qt.resolvedUrl("../../assets/icons/refresh-cw.svg")
    readonly property url zap:           Qt.resolvedUrl("../../assets/icons/zap.svg")
    readonly property url trade:         Qt.resolvedUrl("../../assets/icons/zap.svg")
    readonly property url capital:       Qt.resolvedUrl("../../assets/icons/wallet.svg")
    readonly property url search:        Qt.resolvedUrl("../../assets/icons/search.svg")
    readonly property url close:         Qt.resolvedUrl("../../assets/icons/x.svg")
    readonly property url check:         Qt.resolvedUrl("../../assets/icons/check_white.svg")
    readonly property url collapse:      Qt.resolvedUrl("../../assets/icons/arrow-left.svg")
    readonly property url expand:        Qt.resolvedUrl("../../assets/icons/arrow-right.svg")
    readonly property url chevronDown:   Qt.resolvedUrl("../../assets/icons/chevron-down.svg")
    readonly property url chevronUp:     Qt.resolvedUrl("../../assets/icons/chevron-up.svg")
    readonly property url sun:           Qt.resolvedUrl("../../assets/icons/sun.svg")
    readonly property url moon:          Qt.resolvedUrl("../../assets/icons/moon.svg")
    readonly property url target:        Qt.resolvedUrl("../../assets/icons/crosshair.svg")
    readonly property url fullscreen:    Qt.resolvedUrl("../../assets/icons/maximize.svg")
    readonly property url layers:        Qt.resolvedUrl("../../assets/icons/layers.svg")
    readonly property url info:          Qt.resolvedUrl("../../assets/icons/info.svg")
    readonly property url alert:         Qt.resolvedUrl("../../assets/icons/alert-triangle.svg")

    // --- Finansal & Metrik İkonları ---
    readonly property url coins:         Qt.resolvedUrl("../../assets/icons/coins.svg")
    readonly property url banknote:      Qt.resolvedUrl("../../assets/icons/banknote.svg")
    readonly property url trendingUp:    Qt.resolvedUrl("../../assets/icons/trending-up.svg")
    readonly property url trendingDown:  Qt.resolvedUrl("../../assets/icons/trending-down.svg")
    readonly property url barChart:      Qt.resolvedUrl("../../assets/icons/bar-chart-2.svg")
    readonly property url lineChart:     Qt.resolvedUrl("../../assets/icons/line-chart.svg")
    readonly property url candle:        Qt.resolvedUrl("../../assets/icons/candlestick.svg")
    readonly property url areaChart:     Qt.resolvedUrl("../../assets/icons/area-chart.svg")
    readonly property url fileText:      Qt.resolvedUrl("../../assets/icons/file-text.svg")
    readonly property url users:         Qt.resolvedUrl("../../assets/icons/users.svg")
    readonly property url history:       Qt.resolvedUrl("../../assets/icons/history.svg")
    readonly property url plus:          Qt.resolvedUrl("../../assets/icons/plus.svg")
    readonly property url edit:          Qt.resolvedUrl("../../assets/icons/edit.svg")
    readonly property url trash:         Qt.resolvedUrl("../../assets/icons/trash-2.svg")
    readonly property url dollarSign:    Qt.resolvedUrl("../../assets/icons/dollar-sign.svg")
    readonly property url play:          Qt.resolvedUrl("../../assets/icons/play.svg")
    readonly property url filter:        Qt.resolvedUrl("../../assets/icons/filter.svg")

    function get(name) {
        if (!name) return "";
        switch (name.toLowerCase()) {
            case "dashboard":
            case "genelbakis":    return dashboard;
            case "watchlist":
            case "izlemelisteleri": return watchlist;
            case "portfolio":
            case "modelportfoyler": return portfolio;
            case "stock360":
            case "hisse360":      return stock360;
            case "compare":
            case "karsilastirma": return compare;
            case "screener":
            case "tarayici":      return screener;
            case "planning":
            case "planlama":      return planning;
            case "optimization":
            case "optimizasyon":  return optimization;
            case "ai":
            case "asistan":       return ai;
            case "settings":
            case "ayarlar":       return settings;
            case "refresh":       return refresh;
            case "trade":
            case "hizliislem":
            case "zap":           return zap;
            case "capital":
            case "sermaye":       return capital;
            case "search":        return search;
            case "close":         return close;
            case "check":         return check;
            case "collapse":      return collapse;
            case "expand":        return expand;
            case "chevrondown":   return chevronDown;
            case "chevronup":     return chevronUp;
            case "sun":           return sun;
            case "moon":          return moon;
            case "target":        return target;
            case "fullscreen":    return fullscreen;
            case "layers":
            case "indicators":    return layers;
            case "coins":         return coins;
            case "banknote":      return banknote;
            case "trendingup":    return trendingUp;
            case "trendingdown":  return trendingDown;
            case "barchart":
            case "bar":           return barChart;
            case "linechart":
            case "line":          return lineChart;
            case "candle":        return candle;
            case "areachart":
            case "area":          return areaChart;
            case "filetext":
            case "file-text":     return fileText;
            case "users":         return users;
            case "history":       return history;
            case "info":          return info;
            case "alert":         return alert;
            case "plus":          return plus;
            case "edit":
            case "pencil":        return edit;
            case "trash":
            case "delete":        return trash;
            case "dollarsign":
            case "dollar-sign":   return dollarSign;
            case "play":          return play;
            case "filter":        return filter;
            default:              return Qt.resolvedUrl("../../assets/icons/" + name + ".svg");
        }
    }
}
