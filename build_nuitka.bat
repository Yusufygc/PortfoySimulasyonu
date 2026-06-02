@echo off
setlocal
REM Venv aktif etme kismi
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

echo.
echo Gerekli kutuphaneler kontrol ediliyor...
python -m pip install -r requirements.txt -r requirements-build.txt
if errorlevel 1 (
    echo Hata: Bagimlilik kurulumu basarisiz.
    exit /b 1
)

echo.
echo Release preflight kontrolu calistiriliyor...
python scripts\build_preflight.py
if errorlevel 1 (
    echo Hata: Release preflight basarisiz.
    exit /b 1
)

echo.
echo Nuitka ile exe olusturuluyor...
REM --enable-plugin=numpy KALDIRILDI (Deprecated)
REM --nofollow-import-to=*.tests: Test dosyalarini dahil etme (hizlandirir)
REM --nofollow-import-to=IPython: IPython'u dahil etme
REM --noinclude-numba-mode=nofollow: Numba'yi dahil etme
python -m nuitka --standalone --onefile --enable-plugin=pyqt5 --disable-console --include-package=mysql.connector --include-package=yfinance --include-package=pandas --include-package=openpyxl --windows-icon-from-ico=icons/portfoy-simulasyonu.ico --output-dir=dist --nofollow-import-to=*.tests --nofollow-import-to=IPython --noinclude-numba-mode=nofollow --noinclude-pytest-mode=nofollow app.py
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
