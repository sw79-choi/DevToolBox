@echo off
chcp 65001 >nul
title DevToolBox
cd /d "%~dp0"

where py >nul 2>&1 && (set PY=py) || (set PY=python)

%PY% -c "import PyQt6, pypdf" >nul 2>&1
if errorlevel 1 (
  %PY% -c "import PyQt5, pypdf" >nul 2>&1
  if errorlevel 1 (
    echo [First run] Installing dependencies, please wait...
    %PY% -m pip install -r requirements.txt
    if errorlevel 1 (
      echo.
      echo Dependency installation failed. Is Python installed and on PATH?
      pause
      exit /b 1
    )
  )
)

start "" %PY%w main.py %*
