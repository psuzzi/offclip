@echo off
rem offclip launcher for Windows. Double-click to open the window, or: run.bat --help
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\bootstrap.ps1" %*
if errorlevel 1 (
  echo.
  echo offclip could not start. The lines above say why.
  if not defined CI pause
)
