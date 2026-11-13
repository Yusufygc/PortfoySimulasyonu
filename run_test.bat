@echo off
setlocal
REM Python yorumlayicisi: once proje venv, sonra .venv, sonra PATH (kullaniciya ozel yol yok).
if exist .\venv\Scripts\python.exe (
    set "PYTHON_EXEC=.\venv\Scripts\python.exe"
) else if exist .\.venv\Scripts\python.exe (
    set "PYTHON_EXEC=.\.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXEC=python"
)
set PORTFOYSIM_ENV=test
"%PYTHON_EXEC%" app.py
