<#
    Build a Windows one-file EXE for SCUM Server Manager (PySide6)

    What it does:
    - Creates an isolated build venv (.venv-build)
    - Installs project requirements + PyInstaller
    - Packages PySide6 app as a single .exe
    - Includes configs (json) and Config/ folder as app data

    Output:
    - dist\SCUM-Server-Manager.exe
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Write-Host "=== Building SCUM Server Manager EXE ===" -ForegroundColor Cyan

# Resolve paths
$ScriptDir   = $PSScriptRoot
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir '..')).Path
Push-Location $ProjectRoot

try {
    # Ensure Python
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        throw "Python 3.8+ is required. Install from https://www.python.org/downloads/ and ensure it is on PATH."
    }

    # Create build venv
    $venvPath = Join-Path $ProjectRoot '.venv-build'
    if (-not (Test-Path $venvPath)) {
        Write-Host "Creating virtual environment (.venv-build)..." -ForegroundColor Yellow
        python -m venv $venvPath
    }

    # Determine Python executable inside venv (Windows)
    $venvPython = Join-Path $venvPath 'Scripts/python.exe'
    if (-not (Test-Path $venvPython)) { throw "Failed to locate venv python at $venvPython" }

    # Upgrade pip, install deps + pyinstaller
    & $venvPython -m pip install --upgrade pip wheel setuptools | Out-Null
    & $venvPython -m pip install -r (Join-Path $ProjectRoot 'requirements.txt') | Out-Null
    # Pin a recent PyInstaller known to work well with PySide6
    & $venvPython -m pip install "pyinstaller>=6.6" | Out-Null

    # Build flags
    $name = 'SCUM-Server-Manager'
    $entry = 'scum_server_manager_pyside.py'

    # Collect PySide6 assets explicitly for reliability
    $pyiArgs = @(
        '--noconfirm',
        '--clean',
        '--onefile',
        '--windowed',
        ('--name=' + $name),
        '--collect-all', 'PySide6',
        # Include common project data files
        '--add-data', 'config_presets.json;.',
        '--add-data', 'scum_settings.json;.',
        '--add-data', 'scum_setup.json;.',
        '--add-data', 'Config;Config'
    )

    # Run PyInstaller
    Write-Host "Running PyInstaller..." -ForegroundColor Yellow
    & $venvPython -m PyInstaller @pyiArgs -- $entry

    $exePath = Join-Path $ProjectRoot (Join-Path 'dist' ($name + '.exe'))
    if (Test-Path $exePath) {
        Write-Host "\nBuild succeeded:" -ForegroundColor Green
        Write-Host "  $exePath" -ForegroundColor Green
    }
    else {
        throw "EXE not found at $exePath"
    }

    Write-Host "\nTip: You can now zip the 'dist' folder and share the EXE." -ForegroundColor DarkGray
}
finally {
    Pop-Location
}
