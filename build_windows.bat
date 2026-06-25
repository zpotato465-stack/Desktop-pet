@echo off
REM Build script for Windows .exe
REM Run this on a Windows machine

echo 🦆  Duck Desktop Pet — Windows Build
echo ======================================

pip install -r requirements.txt
pyinstaller --clean build_windows.spec

echo.
echo Done! Your .exe is in:
echo   dist\duck that carries you over a disproportionately small gap.exe
pause
