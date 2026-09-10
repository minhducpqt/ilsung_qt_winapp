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
if exist "dist\QTWinApp" (
    rmdir /s /q "dist\QTWinApp"
)

pyinstaller --noconfirm --clean QTWinApp.spec
