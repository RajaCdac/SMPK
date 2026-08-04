@echo off
REM Copy first-pension fi_* tables from MySQL finance (3307) → smpk_pension (3306).
REM Does NOT touch first_pension_* / accounts_* tables.
REM
REM Examples:
REM   sync_finance_to_smpk.bat list
REM   sync_finance_to_smpk.bat dry-run
REM   sync_finance_to_smpk.bat
REM   sync_finance_to_smpk.bat create-missing
REM   sync_finance_to_smpk.bat yes

set SCRIPT_DIR=%~dp0
set PYTHON=%SCRIPT_DIR%..\..\venv\Scripts\python.exe

if not exist "%PYTHON%" (
  echo Python venv not found at %PYTHON%
  exit /b 1
)

if /I "%~1"=="list" (
  "%PYTHON%" "%SCRIPT_DIR%sync_finance_to_smpk.py" --list-only
  exit /b %ERRORLEVEL%
)

if /I "%~1"=="dry-run" (
  "%PYTHON%" "%SCRIPT_DIR%sync_finance_to_smpk.py" --dry-run --yes
  exit /b %ERRORLEVEL%
)

if /I "%~1"=="yes" (
  "%PYTHON%" "%SCRIPT_DIR%sync_finance_to_smpk.py" --create-missing --yes
  exit /b %ERRORLEVEL%
)

if /I "%~1"=="create-missing" (
  "%PYTHON%" "%SCRIPT_DIR%sync_finance_to_smpk.py" --create-missing --yes
  exit /b %ERRORLEVEL%
)

if "%~1"=="" (
  "%PYTHON%" "%SCRIPT_DIR%sync_finance_to_smpk.py" --create-missing
  exit /b %ERRORLEVEL%
)

echo Usage:
echo   sync_finance_to_smpk.bat list
echo   sync_finance_to_smpk.bat dry-run
echo   sync_finance_to_smpk.bat
echo   sync_finance_to_smpk.bat create-missing
echo   sync_finance_to_smpk.bat yes
exit /b 1
