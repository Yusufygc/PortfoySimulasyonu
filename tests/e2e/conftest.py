"""E2E ürün testi düzeneği: tek oturumluk gerçek uygulama kabuğu, taze test veritabanı, başarısızlıkta ekran görüntüsü.

Çalıştırma: `python -m pytest -m e2e tests/e2e -v`  (varsayılan pytest koşusundan hariçtir, bkz. pytest.ini).
Testler tek bir kullanıcının gününü sırayla anlatır (dosya adı sırası); her biri kendi ön koşulunu doğrular.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

# Yazılım çizim arka ucu: GPU/ekran gerektirmez, CI'da da aynı çalışır. Qt'nin ilk kullanımından önce ayarlanmalıdır.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
# Offscreen platformda sistem yazı tipleri yüklenmez (metin kutu olarak çizilir ve satırlar gerçekte olduğundan çok daha geniş
# ölçülür). Windows yazı tipleri dizini verilince yerleşim ölçüleri gerçek uygulamayla aynı olur.
if os.name == "nt" and Path(r"C:\Windows\Fonts").exists():
    os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")

from tests.e2e.human import Human  # noqa: E402
from tests.e2e.shell import ROOT, build_shell, network_blocked, prepare_test_db, qml_warnings  # noqa: E402

ARTIFACT_ROOT = ROOT / "reports" / "e2e"

# Bilinen ve kabul edilmiş QML uyarıları; yeni bir uyarı çıkarsa test kırılır.
KNOWN_QML_WARNINGS = (
    "ChartInfoCard.qml:56:13: QML MouseArea: Detected anchors on an item that is managed by a layout",
)


def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: gerçek kabukta fare/klavye süren ürün testleri (varsayılan koşudan hariç).")


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "/tests/e2e/" in Path(str(item.fspath)).as_posix():
            item.add_marker(pytest.mark.e2e)


@pytest.fixture(scope="session")
def e2e_run_dir() -> Path:
    run_dir = ARTIFACT_ROOT / time.strftime("%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


@pytest.fixture(scope="session")
def human(tmp_path_factory, e2e_run_dir):
    """Tek oturumluk kabuk: boş şemadan taze SQLite + piyasa geçmişi kopyası, ağ kapalı."""
    work = tmp_path_factory.mktemp("e2e_db")
    sqlite_path, duck_path = prepare_test_db(work)
    with network_blocked():
        app, engine, controllers, container = build_shell(sqlite_path, duck_path)
        driver = Human(engine, controllers, container, shots_dir=e2e_run_dir / "screens")
        driver.work = work
        driver.sqlite_path = sqlite_path
        driver.duck_path = duck_path
        driver.pump(40, 0.01)
        yield driver


@pytest.fixture(autouse=True)
def _clean_screen(request, human):
    """Her test temiz ekranla başlar (açık iletişim kutusu kalmaz) ve başarısızlıkta ekran görüntüsü bırakır."""
    human.cancel()
    yield
    report = getattr(request.node, "rep_call", None)
    if report is not None and report.failed:
        human.screenshot(f"FAIL_{request.node.name}")


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    setattr(item, "rep_" + outcome.get_result().when, outcome.get_result())


@pytest.fixture
def unexpected_qml_warnings():
    def collect():
        return [w for w in qml_warnings() if not any(known in w for known in KNOWN_QML_WARNINGS)]

    return collect
