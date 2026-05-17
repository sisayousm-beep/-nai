@echo off
cd /d "%~dp0"
where pythonw >nul 2>&1
if errorlevel 1 (
    echo pythonw.exe not found in PATH. Falling back to python.
    start "" python "%~dp0proxy.py"
) else (
    start "" pythonw "%~dp0proxy.py"
)
