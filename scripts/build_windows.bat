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

pyinstaller --noconfirm --clean ILSungQTWinApp.spec
