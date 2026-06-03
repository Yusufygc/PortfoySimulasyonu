from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage

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
        self.setPage(SilentWebEnginePage(self))
