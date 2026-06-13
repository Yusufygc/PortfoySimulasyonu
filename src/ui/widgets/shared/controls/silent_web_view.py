from pathlib import Path

from src.qt_compat.qtcore import QDir, QStandardPaths, Qt
from src.qt_compat.qtgui import QColor
from src.qt_compat.qtwebengine import QWebEnginePage, QWebEngineView

class SilentWebEnginePage(QWebEnginePage):
    """
    Özel bir WebEnginePage sınıfı. Plotly gibi kütüphanelerin
    desteklenmeyen CSS özellikleri nedeniyle konsola fırlattığı
    'Ignored CSSStyleSheet.insertRule error' gibi sinir bozucu
    JS hatalarını ve konsol mesajlarını gizler.
    """
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        # Eğer loglanmasını istemediğimiz bilindik bir hata ise yoksayıyoruz.
        if "Ignored CSSStyleSheet.insertRule error" in message:
            return
        
        # Diğer JS mesajlarını tamamen gizleyebiliriz,
        # çünkü uygulama içinde kullanıcıyı ilgilendiren bir web JS log'u yok.
        pass

class SilentWebEngineView(QWebEngineView):
    """
    Gereksiz JavaScript konsol çıktılarını engelleyen QWebEngineView.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.NoFocus)
        self.setPage(SilentWebEnginePage(self))
        self.page().setBackgroundColor(QColor(0, 0, 0, 0))
        self._ensure_download_handler()

    def _ensure_download_handler(self) -> None:
        profile = self.page().profile()
        if profile.property("_silentDownloadsBound"):
            return

        profile.setProperty("_silentDownloadsBound", True)
        profile.downloadRequested.connect(self._handle_download_requested)

    @staticmethod
    def _handle_download_requested(download_item) -> None:
        download_dir = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
        if not download_dir:
            download_dir = QDir.homePath()

        target_dir = Path(download_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        filename = download_item.downloadFileName() or "newplot.png"
        download_item.setDownloadDirectory(str(target_dir))
        download_item.setDownloadFileName(filename)
        download_item.accept()
