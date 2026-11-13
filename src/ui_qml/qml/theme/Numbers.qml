pragma Singleton
import QtQuick

// Kullanıcının yazdığı sayı metnini okur. Kurallar Python tarafındaki
// controllers/number_input.parse_decimal_text ile aynıdır (test: test_numbers_singleton.py):
// '1.234,56' -> 1234.56, '50.000' -> 50000 (nokta binlik ayracı), '1234.56' -> 1234.56, '25,5' -> 25.5.
// JavaScript parseFloat Türkçe biçimi yanlış okur ('50.000' -> 50); para girişlerinde yalnızca bu kullanılır.
QtObject {
    readonly property var _thousandsOnly: /^\d{1,3}(\.\d{3})+$/
    readonly property var _plainNumber: /^[+-]?(\d+(\.\d*)?|\.\d+)$/

    // Sayı değilse NaN döner
    function parse(text) {
        let raw = String(text === undefined || text === null ? "" : text).replace(/\s/g, "")
        if (raw === "")
            return NaN
        if (raw.indexOf(",") >= 0)
            raw = raw.replace(/\./g, "").replace(/,/g, ".")
        else if (_thousandsOnly.test(raw))
            raw = raw.replace(/\./g, "")
        if (!_plainNumber.test(raw))
            return NaN
        const value = Number(raw)
        return isFinite(value) ? value : NaN
    }

    // Sayı değilse veya boşsa `fallback`
    function parseOr(text, fallback) {
        const value = parse(text)
        return isNaN(value) ? fallback : value
    }

    // Tam sayı (lot, adet); tam sayı değilse NaN
    function parseInteger(text) {
        const value = parse(text)
        return (isNaN(value) || Math.floor(value) !== value) ? NaN : value
    }
}
