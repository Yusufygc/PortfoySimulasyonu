"""QML metin yönetimi: kullanıcı metinleri Strings.qml'de durur ve her Strings referansı tanımlıdır."""
from __future__ import annotations

import re
from pathlib import Path

QML_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "ui_qml" / "qml"
STRINGS_FILE = QML_DIR / "theme" / "Strings.qml"

LITERAL_PROPERTY = re.compile(
    r"\b(text|placeholderText|title|ToolTip\.text|description|headerText|buttonText|emptyText|subtitle|label|hint|message|caption)"
    r"\s*:\s*\"([^\"]*[A-Za-zÇĞİÖŞÜçğıöşü]{2}[^\"]*)\""
)

# Kullanıcı metni olmayan sabitler: örnek veri, bileşen varsayılanı, para birimi kodu, giriş alanı başlangıç değeri
ALLOWED_LITERALS = {
    ("components/AssetAllocationCard.qml", "BIST Hisse Senetleri"),
    ("components/AssetAllocationCard.qml", "Eurobond / Fonlar"),
    ("components/AssetAllocationCard.qml", "TL Nakit & Mevduat"),
    ("components/MetricCard.qml", "Metrik Başlığı"),
    ("components/PlanningDcaTab.qml", "THYAO FROTO"),
    ("views/ComparisonView.qml", "TL"),
    ("views/ComparisonView.qml", "USD"),
    ("views/PlaceholderView.qml", "Sayfa Başlığı"),
    ("views/PlaceholderView.qml", "Bu modül dönüşüm planının sonraki fazında TradingView / QML bileşenleriyle inşa edilecektir."),
}


STRING_LITERAL = re.compile(r'"((?:[^"\\]|\\.)*)"')
TURKISH_LETTER = re.compile(r"[çğıöşüÇĞİÖŞÜ]")

# Türkçe harf içeren ama kullanıcı metni olmayan sabitler: controller ile değiş tokuş edilen değerler ve durum kodları
ALLOWED_TURKISH_LITERALS = {
    ("components/ComparisonChartCard.qml", "Tümü"),          # dönem etiketi, controller.setPeriod değeri
    ("components/EditGoalDialog.qml", "YÜKSEK"),             # hedef önceliği değerleri (controller ile aynı dilde)
    ("components/EditGoalDialog.qml", "DÜŞÜK"),
    ("components/EditGoalDialog.qml", "ORTA"),
    ("components/NewGoalDialog.qml", "YÜKSEK"),
    ("components/NewGoalDialog.qml", "DÜŞÜK"),
    ("components/NewGoalDialog.qml", "ORTA"),
    ("components/PlanningGoalsTab.qml", "BAŞARILI"),         # fizibilite durum kodu
    ("components/PlanningGoalsTab.qml", "YÜKSEK"),
    ("components/PlanningGoalsTab.qml", "DÜŞÜK"),
    ("views/ComparisonView.qml", "ÖZEL"),                    # dönem etiketi
    ("views/SettingsView.qml", "Başarılı"),                  # API testi sonuç metninde aranan kelime
    ("components/MetricCard.qml", "Metrik Başlığı"),
    ("views/PlaceholderView.qml", "Sayfa Başlığı"),
    ("views/PlaceholderView.qml", "Bu modül dönüşüm planının sonraki fazında TradingView / QML bileşenleriyle inşa edilecektir."),
}


def _qml_files():
    return sorted(path for path in QML_DIR.rglob("*.qml") if path != STRINGS_FILE)


def test_every_strings_reference_is_defined():
    catalog = STRINGS_FILE.read_text(encoding="utf-8")
    defined = set(re.findall(r"property \w+ (\w+):", catalog)) | set(re.findall(r"function (\w+)\(", catalog))

    missing = sorted(
        f"{path.relative_to(QML_DIR).as_posix()}: Strings.{key}"
        for path in _qml_files()
        for key in set(re.findall(r"\bStrings\.(\w+)", path.read_text(encoding="utf-8")))
        if key not in defined
    )

    assert missing == [], "Strings.qml'de tanımsız anahtar:\n" + "\n".join(missing)


def test_qml_files_do_not_hardcode_user_facing_text():
    violations = []
    for path in _qml_files():
        relative = path.relative_to(QML_DIR).as_posix()
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for match in LITERAL_PROPERTY.finditer(line.split("//", 1)[0]):
                if (relative, match.group(2)) not in ALLOWED_LITERALS:
                    violations.append(f"{relative}:{number}: {match.group(1)}: \"{match.group(2)}\"")

    assert violations == [], "Metinler Strings.qml'e taşınmalı:\n" + "\n".join(violations)


def test_qml_files_do_not_embed_turkish_string_literals():
    """Property adından bağımsız: Türkçe harf içeren her dize literali Strings.qml'de olmalı (izin listesi hariç)."""
    violations = []
    for path in _qml_files():
        relative = path.relative_to(QML_DIR).as_posix()
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for match in STRING_LITERAL.finditer(line.split("//", 1)[0]):
                literal = match.group(1)
                if TURKISH_LETTER.search(literal) and (relative, literal) not in ALLOWED_TURKISH_LITERALS:
                    violations.append(f"{relative}:{number}: \"{literal}\"")

    assert violations == [], "Türkçe metinler Strings.qml'e taşınmalı:\n" + "\n".join(violations)


def test_strings_catalog_has_no_duplicate_keys():
    keys = re.findall(r"property \w+ (\w+):", STRINGS_FILE.read_text(encoding="utf-8"))
    duplicates = sorted({key for key in keys if keys.count(key) > 1})

    assert duplicates == []
