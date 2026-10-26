@echo off
REM ---------------------------------------------------------------
REM  TwitchFix — сборка .exe одной командой (Windows 10/11)
REM ---------------------------------------------------------------
setlocal
cd /d "%~dp0"

echo [*] Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller pillow
if errorlevel 1 (
    echo [!] Failed to install dependencies.
    pause
    exit /b 1
)

echo [*] Building TwitchFix.exe ...
python build.py
if errorlevel 1 (
    echo [!] Build failed. See the PyInstaller output above.
    pause
    exit /b 1
)

echo.
echo [OK] Build finished: dist\TwitchFix.exe
echo      Run it as Administrator when you plan to apply fixes.
pause
endlocal
