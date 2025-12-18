@echo off
setlocal enabledelayedexpansion

REM Run this from Windows Task Scheduler (daily). Writes logs to logs\scheduler.

REM Ensure UTF-8 so redirected logs don't crash on non-ASCII output.
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

cd /d "%~dp0.."

if not exist "logs\scheduler" mkdir "logs\scheduler"

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH-mm-ss"') do set TS=%%i
set LOG=logs\scheduler\scrape_!TS!.log

echo [%date% %time%] Starting daily scrape... > "!LOG!"
echo Repo: %cd%>> "!LOG!"

if exist ".venv\Scripts\python.exe" (
  set PY=.venv\Scripts\python.exe
) else (
  set PY=python
)

REM Initialize DB tables (safe to run repeatedly), then run jobs+news.
"!PY!" -c "from src.news.models import init_db; init_db()" >> "!LOG!" 2>&1
"!PY!" -m src.main --all --days 7 >> "!LOG!" 2>&1

echo [%date% %time%] Done.>> "!LOG!"
endlocal
