@echo off
REM SQLiteStudio Professional - Build Executable
REM Copyright (c) 2025 SCUM Server Manager Project

echo ======================================
echo SQLiteStudio Pro - Executable Builder
echo ======================================
echo.

echo [1/3] Checking PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
) else (
    echo PyInstaller is already installed.
)
echo.

echo [2/3] Building executable...
pyinstaller --onefile --windowed --name "SQLiteStudio-Pro" --icon="%~dp0Config\server.cfg" run_sqlitestudio_standalone.py

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)
echo.

echo [3/3] Build complete!
echo.
echo Executable location: dist\SQLiteStudio-Pro.exe
echo.
echo You can now distribute SQLiteStudio-Pro.exe to users!
echo No Python installation required for users.
echo.
echo Remember to include:
echo - LICENSE file
echo - README.md
echo - Copyright notice
echo.
pause
