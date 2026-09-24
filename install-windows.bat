@echo off
rem Double-click this file to install polish-academic-skills into every AI tool
rem found on this computer (Claude Code, Codex, Gemini CLI, Cursor, Copilot, ...).
rem Extra options are passed through, e.g.:  install-windows.bat --zip
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py -3 install.py %*
    goto done
)
where python >nul 2>nul
if not errorlevel 1 (
    python install.py %*
    goto done
)
echo Python 3 was not found on this computer.
echo Install it from https://www.python.org/downloads/ and tick
echo "Add python.exe to PATH" in the installer, then run this file again.
:done
echo.
pause
