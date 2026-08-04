@echo off
REM Dump one Oracle FINANCE table into MySQL database finance (port 3307).
REM Usage:
REM   dump_oracle_table.bat FI_LA_TH_LVAPPL
REM   dump_oracle_table.bat FI_PN_MH_OLDBILL_PARAM --drop

set SCRIPT_DIR=%~dp0
set PYTHON=%SCRIPT_DIR%..\..\venv\Scripts\python.exe

if not exist "%PYTHON%" (
  echo Python venv not found at %PYTHON%
  exit /b 1
)

if "%~1"=="" (
  echo Usage: dump_oracle_table.bat TABLE_NAME [--drop] [--truncate] [--batch-size N]
  echo        dump_oracle_table.bat --apply-pending-fks
  exit /b 1
)

if /I "%~1"=="--apply-pending-fks" (
  "%PYTHON%" "%SCRIPT_DIR%oracle_table_to_mysql.py" --apply-pending-fks
  exit /b %ERRORLEVEL%
)

"%PYTHON%" "%SCRIPT_DIR%oracle_table_to_mysql.py" %*
