from pathlib import Path

import pytest

pytest.importorskip("PyQt5")

from src.ui.widgets.shared.controls.silent_web_view import SilentWebEngineView


class _FakeDownloadItem:
    def __init__(self, filename: str = "newplot.png") -> None:
        self._filename = filename
        self.saved_path = None
        self.accepted = False

    def downloadFileName(self) -> str:
        return self._filename

    def setPath(self, path: str) -> None:
        self.saved_path = path

    def accept(self) -> None:
        self.accepted = True


def test_download_request_is_redirected_to_downloads_folder(tmp_path, monkeypatch):
    from src.ui.widgets.shared.controls import silent_web_view

    monkeypatch.setattr(
        silent_web_view.QStandardPaths,
        "writableLocation",
        lambda _location: str(tmp_path),
    )
    item = _FakeDownloadItem("chart-export.png")

    SilentWebEngineView._handle_download_requested(item)

    assert item.accepted is True
    assert item.saved_path == str(tmp_path / "chart-export.png")


def test_download_request_uses_default_plotly_filename_when_empty(tmp_path, monkeypatch):
    from src.ui.widgets.shared.controls import silent_web_view

    monkeypatch.setattr(
        silent_web_view.QStandardPaths,
        "writableLocation",
        lambda _location: str(tmp_path),
    )
    item = _FakeDownloadItem("")

    SilentWebEngineView._handle_download_requested(item)

    assert Path(item.saved_path).name == "newplot.png"
    assert item.accepted is True
