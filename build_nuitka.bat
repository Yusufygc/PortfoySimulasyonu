@echo off
REM Venv aktif etme kismi
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

echo.
echo Gerekli kutuphaneler kontrol ediliyor...
pip install nuitka pyqt5 mysql-connector-python yfinance pandas openpyxl

echo.
echo Nuitka ile exe olusturuluyor...
REM --enable-plugin=numpy KALDIRILDI (Deprecated)
REM --nofollow-import-to=*.tests: Test dosyalarini dahil etme (hizlandirir)
REM --nofollow-import-to=IPython: IPython'u dahil etme
REM --noinclude-numba-mode=nofollow: Numba'yi dahil etme
python -m nuitka --standalone --onefile --enable-plugin=pyqt5 --disable-console --include-package=mysql.connector --include-package=yfinance --include-package=pandas --include-package=openpyxl --windows-icon-from-ico=icons/wallet.ico --include-data-file=.env=.env --output-dir=dist --nofollow-import-to=*.tests --nofollow-import-to=IPython --noinclude-numba-mode=nofollow --noinclude-pytest-mode=nofollow app.py

echo.
echo Islem tamamlandi.
pause