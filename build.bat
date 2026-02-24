@echo off
title SHIELD — Build Tool by SaruProDev

echo.
echo   =====================================================
echo    SHIELD v2 — USB Kill Switch
echo    by SaruProDev ^| github.com/SaruProDev
echo    No UAC. No Delay. No Mercy.
echo   =====================================================
echo.

:: ── Check Python ──────────────────────────────────────────
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo   [!] Python not found.
    echo       Download it from https://python.org
    echo       Make sure to tick "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do echo   [check] %%i found.

:: ── Check / Install PyInstaller ───────────────────────────
echo.
pip show pyinstaller >nul 2>&1
IF ERRORLEVEL 1 (
    echo   [*] PyInstaller not found. Installing...
    pip install pyinstaller --quiet
    echo   [check] PyInstaller installed.
) ELSE (
    echo   [check] PyInstaller already installed.
)

:: ── Build ─────────────────────────────────────────────────
echo.
echo   [*] Compiling killswitch.py to shield.exe ...
echo       This takes 30-60 seconds. Do not close this window.
echo.

python -m PyInstaller ^
    --onefile ^
    --noconsole ^
    --uac-admin ^
    --name "shield" ^
    killswitch.py >nul 2>&1

echo.
IF EXIST "dist\shield.exe" (
    echo   [SUCCESS] Compilation successful!
    echo.

    IF NOT EXIST "SHIELD_USB" mkdir SHIELD_USB
    copy "dist\shield.exe" "SHIELD_USB\shield.exe" >nul

    echo   shield.exe is ready in .\SHIELD_USB\
    echo.
    echo   NEXT STEPS:
    echo   1. Label your USB drive: SHIELD
    echo   2. Copy shield.exe to the ROOT of the USB
    echo   3. Run setup_shield.ps1 as Administrator
    echo   4. Log out and back in
    echo   5. Plug in USB = instant shutdown
) ELSE (
    echo   [FAILED] Build failed. Check output above for errors.
    echo   Common fix: right-click build.bat and Run as Administrator.
)

echo.
pause
