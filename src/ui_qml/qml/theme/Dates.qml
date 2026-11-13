pragma Singleton
import QtQuick

// Tarih alanlarının başlangıç değerleri. Biçim her yerde GG.AA.YYYY; Python tarafındaki
// controllers/date_input.format_date_text ile aynıdır (test: test_date_input.py). Bileşenlerde elle
// getFullYear() + "-" + ... üretilmez.
QtObject {
    function pad(value) {
        return String(value).padStart(2, "0")
    }

    // JavaScript Date -> "GG.AA.YYYY"
    function format(date) {
        return pad(date.getDate()) + "." + pad(date.getMonth() + 1) + "." + date.getFullYear()
    }

    function today() {
        return format(new Date())
    }

    function todayPlusYears(years) {
        const d = new Date()
        d.setFullYear(d.getFullYear() + years)
        return format(d)
    }
}
