@echo off
setlocal
if not exist "%~dp0runtime\pythonw.exe" (
  echo Extract the complete Windows portable ZIP before running this launcher.
  pause
  exit /b 1
)
start "" "%~dp0runtime\pythonw.exe" "%~dp0desktop_app.py" %*
