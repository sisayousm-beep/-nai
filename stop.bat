@echo off
cd /d "%~dp0"
if exist ".proxy.pid" (
    for /f "usebackq tokens=*" %%i in (".proxy.pid") do (
        echo Stopping proxy ^(pid %%i^) ...
        taskkill /PID %%i /F >nul 2>&1
    )
    del ".proxy.pid" >nul 2>&1
    echo Stopped.
) else (
    echo No running proxy found ^(.proxy.pid missing^).
    echo If proxy is still running you can also use:
    echo   taskkill /IM pythonw.exe /F
)
timeout /t 2 >nul
