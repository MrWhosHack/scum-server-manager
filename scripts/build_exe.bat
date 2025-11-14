@echo off
setlocal
pushd %~dp0
rem Wrapper to call the PowerShell builder
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_windows_exe.ps1"
set ERR=%ERRORLEVEL%
popd
exit /b %ERR%
