@echo off
setlocal
cd /d "%~dp0.."

if not exist ".venv" (
    python -m venv .venv
)

call ".venv\Scripts\activate.bat"
python -m pip install -r requirements.txt

if exist "build" (
    rmdir /s /q "build"
)
if exist "dist\ILSungQTWinApp" (
    rmdir /s /q "dist\ILSungQTWinApp"
)
if exist "dist\ILSungQTWinApp.exe" (
    del /f /q "dist\ILSungQTWinApp.exe"
)

pyinstaller --noconfirm --clean ILSungQTWinApp.spec
