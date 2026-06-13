import pytest

pytest.importorskip("PySide6")

from src.ui.widgets.shared.controls.silent_web_view import SilentWebEngineView


class _FakeDownloadItem:
    def __init__(self, filename: str = "newplot.png") -> None:
        self._filename = filename
        self.download_directory = None
        self.download_file_name = None
        self.accepted = False

    def downloadFileName(self) -> str:
        return self._filename

    def setDownloadDirectory(self, path: str) -> None:
        self.download_directory = path

    def setDownloadFileName(self, filename: str) -> None:
        self.download_file_name = filename

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
    assert item.download_directory == str(tmp_path)
    assert item.download_file_name == "chart-export.png"


def test_download_request_uses_default_plotly_filename_when_empty(tmp_path, monkeypatch):
    from src.ui.widgets.shared.controls import silent_web_view

    monkeypatch.setattr(
        silent_web_view.QStandardPaths,
        "writableLocation",
        lambda _location: str(tmp_path),
    )
    item = _FakeDownloadItem("")

    SilentWebEngineView._handle_download_requested(item)

    assert item.download_directory == str(tmp_path)
    assert item.download_file_name == "newplot.png"
    assert item.accepted is True
