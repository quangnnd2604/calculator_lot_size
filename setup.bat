@echo off
REM setup.bat — Windows environment setup for FX Lot Master

echo ==> Checking Python version...
python --version
IF ERRORLEVEL 1 (
    echo ERROR: Python not found. Install from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ==> Creating virtual environment in .\venv ...
python -m venv venv

echo ==> Activating virtual environment...
call venv\Scripts\activate.bat

echo ==> Upgrading pip...
pip install --upgrade pip

echo ==> Installing dependencies...
pip install -r requirements.txt

echo.
echo [OK] Setup complete!
echo.
echo To run the app:
echo   venv\Scripts\activate
echo   python main.py
echo.
echo To build a Windows .exe:
echo   venv\Scripts\activate
echo   pyinstaller fx_lot_master.spec
echo.
pause
