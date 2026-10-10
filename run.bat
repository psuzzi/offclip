@echo off
rem offclip launcher for Windows. Double-click to open the window, or: run.bat --help
setlocal
cd /d "%~dp0"

set "PY="
where py >nul 2>&1 && py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1 && set "PY=py -3"
if not defined PY where python >nul 2>&1 && python -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1 && set "PY=python"

if not exist ".venv\Scripts\python.exe" (
  if not defined PY (
    echo offclip needs Python 3.9 or newer.
    echo Install it from https://www.python.org/downloads/windows/ and tick "Add python.exe to PATH",
    echo then run this file again.
    pause
    exit /b 1
  )
  echo First run: preparing a private Python environment in .venv ^(one-time, needs internet^)...
  %PY% -m venv .venv || (echo Could not create .venv & pause & exit /b 1)
  ".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
  ".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt || (echo Install failed & pause & exit /b 1)
  ".venv\Scripts\python.exe" -c "from static_ffmpeg import run; run.get_or_fetch_platform_executables_else_raise()" || echo Warning: could not fetch ffmpeg now; it will be retried on first download.
) else (
  rem Keep yt-dlp current: a stale yt-dlp is the usual reason downloads stop working.
  ".venv\Scripts\python.exe" -m pip install --quiet --upgrade --disable-pip-version-check --timeout 10 --retries 1 yt-dlp >nul 2>&1
)

if "%~1"=="" (
  ".venv\Scripts\python.exe" -c "import tkinter" >nul 2>&1 || (
    echo The window needs Tkinter. Re-run the Python installer from python.org, choose Modify,
    echo and tick "tcl/tk and IDLE". Then delete the .venv folder and start offclip again.
    pause
    exit /b 1
  )
  start "" ".venv\Scripts\pythonw.exe" -m offclip
) else (
  ".venv\Scripts\python.exe" -m offclip %*
)
endlocal
