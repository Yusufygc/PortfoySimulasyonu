from scripts.measure_change_footprint import MARKER, parse_log, summarize

LOG = (
    f"{MARKER}aaa111 ekle: yeni özellik\n\n"
    "src/application/services/x.py\nsrc/ui_qml/qml/theme/Strings.qml\nsrc/ui_qml/app.py\ntests/test_x.py\n"
    f"{MARKER}bbb222 düzelt: hata\n\nsrc/a.py\n"
    f"{MARKER}ccc333 güncelle: davranış\n\nsrc/a.py\nsrc/b.qml\ndocs/wiki/log.md\nsrc/c.txt\n"
)


def test_only_feature_commits_and_source_files_are_counted():
    footprints = parse_log(LOG)
    assert [(f.sha, f.sources, f.hubs) for f in footprints] == [("aaa111", 3, 2), ("ccc333", 2, 0)]


def test_summary_reports_median_and_hub_rate():
    text = summarize(parse_log(LOG))
    assert "Özellik commit'i: 2" in text
    assert "Kaynak dosya medyanı: 2.5" in text
    assert "Kayıt merkezine dokunan commit: 1 (%50)" in text
    assert "Commit başına merkez dokunuşu: 1.00" in text


def test_empty_log():
    assert summarize(parse_log("")) == "Özellik commit'i bulunamadı."
