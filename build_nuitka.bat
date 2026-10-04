@echo off
setlocal

if exist .\venv\Scripts\python.exe (
    set "PYTHON_EXEC=.\venv\Scripts\python.exe"
) else if exist .\.venv\Scripts\python.exe (
    set "PYTHON_EXEC=.\.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXEC=python"
)

echo.
echo Gerekli kutuphaneler kontrol ediliyor...
"%PYTHON_EXEC%" -m pip install -r requirements.txt -r requirements-build.txt
if errorlevel 1 (
    echo Hata: Bagimlilik kurulumu basarisiz.
    exit /b 1
)

echo.
echo Release preflight kontrolu calistiriliyor...
"%PYTHON_EXEC%" scripts\build_preflight.py
if errorlevel 1 (
    echo Hata: Release preflight basarisiz.
    exit /b 1
)

echo.
echo Nuitka ile exe olusturuluyor (PySide6 + QML + Data)...
REM --enable-plugin=pyside6: PySide6, QtQuick ve WebEngine destegi
REM --include-data-dir=src/ui_qml=src/ui_qml: QML dosyalari, SVG ikonlari ve HTML sablonlari
REM data/ dizini bilerek pakete GOMULMEZ: gercek portfolio.db ve market_history.duckdb kisisel veri icerir.
REM Uygulama ilk acilista bos veritabanini olusturur (scripts/build_preflight.py bu kurali denetler).
"%PYTHON_EXEC%" -m nuitka --standalone --onefile --enable-plugin=pyside6 --include-data-dir=src/ui_qml=src/ui_qml --disable-console --include-package=yfinance --include-package=pandas --include-package=openpyxl --include-package=sqlalchemy --windows-icon-from-ico=icons/icon.ico --output-dir=dist --nofollow-import-to=*.tests --nofollow-import-to=IPython --noinclude-numba-mode=nofollow --noinclude-pytest-mode=nofollow app.py
if errorlevel 1 (
    echo Hata: Nuitka build basarisiz.
    exit /b 1
)

if exist dist\.env (
    echo Hata: dist\.env dagitim paketine girmemeli.
    exit /b 1
)

echo.
echo Islem tamamlandi.
pause
