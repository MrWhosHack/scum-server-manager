@echo off
echo ========================================
echo   SCUM Server Manager v2.0
echo   Performance Optimized Edition
echo ========================================
echo.

pushd %~dp0

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Running with administrator privileges
) else (
    echo Requesting administrator privileges...
    powershell "start-process '%~f0' -verb runas"
    exit /b
)

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

REM Check if required modules are installed
python -c "import PySide6; import psutil" >nul 2>&1
if errorlevel 1 (
    echo Installing required modules...
    pip install PySide6 psutil --quiet
    if errorlevel 1 (
        echo ERROR: Failed to install required modules
        pause
        exit /b 1
    )
)

echo Starting optimized SCUM Server Manager...
echo.
echo Performance features enabled:
echo  * Intelligent system metrics caching (500ms)
echo  * Lazy tab loading (loads on demand)
echo  * Event-driven player updates
echo  * Optimized database queries
echo.

python "scum_server_manager_pyside.py"

popd
echo.
echo SCUM Server Manager closed.
pause
    