pragma Singleton
import QtQuick

// Tarih ve saat alanlarının başlangıç değerleri. Biçim her yerde GG.AA.YYYY ve SS:DD; Python tarafındaki
// controllers/date_input.format_date_text / format_time_text ile aynıdır (test: test_date_input.py). Bileşenlerde elle
// getFullYear() / getHours() ile metin üretilmez.
QtObject {
    function pad(value) {
        return String(value).padStart(2, "0")
    }

    // JavaScript Date -> "GG.AA.YYYY"
    function format(date) {
        return pad(date.getDate()) + "." + pad(date.getMonth() + 1) + "." + date.getFullYear()
    }

    // JavaScript Date -> "SS:DD"
    function formatTime(date) {
        return pad(date.getHours()) + ":" + pad(date.getMinutes())
    }

    function nowTime() {
        return formatTime(new Date())
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
