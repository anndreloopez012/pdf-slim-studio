@echo off
setlocal
cd /d "%~dp0\..\.."
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_windows.ps1"
if errorlevel 1 (
  echo.
  echo La compilacion fallo. Revisa el mensaje anterior.
  pause
  exit /b 1
)
echo.
echo Compilacion terminada correctamente.
pause

