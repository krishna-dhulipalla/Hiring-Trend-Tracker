@echo off
setlocal

REM Relaunch hidden (best-effort). Parent console may still exist briefly.
if /i not "%~1"=="--hidden" (
  powershell -NoProfile -WindowStyle Hidden -Command ^
    "Start-Process -FilePath cmd.exe -WindowStyle Hidden -WorkingDirectory '%~dp0' -ArgumentList '/c', '""%~f0"" --hidden'" ^
    >nul 2>&1
  exit /b
)

chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

cd /d "%~dp0.."

if exist ".venv\Scripts\python.exe" (
  set "PY=%CD%\.venv\Scripts\python.exe"
) else (
  set "PY=python"
)

"%PY%" -m streamlit run dashboard\Overview.py --server.port 8501 --browser.gatherUsageStats false

endlocal
