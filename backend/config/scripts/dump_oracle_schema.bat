@echo off
REM Batch dump Oracle FINANCE tables into MySQL finance (port 3307).
REM
REM Examples:
REM   dump_oracle_schema.bat first-pension
REM   dump_oracle_schema.bat all
REM   dump_oracle_schema.bat resume-first-pension
REM   dump_oracle_schema.bat apply-fks

set SCRIPT_DIR=%~dp0
set PYTHON=%SCRIPT_DIR%..\..\venv\Scripts\python.exe

if not exist "%PYTHON%" (
  echo Python venv not found at %PYTHON%
  exit /b 1
)

if /I "%~1"=="first-pension" (
  "%PYTHON%" "%SCRIPT_DIR%oracle_schema_to_mysql.py" --prefix FI_PN --prefix FI_XX --prefix FI_LA --prefix FI_PR --drop
  exit /b %ERRORLEVEL%
)

if /I "%~1"=="all" (
  "%PYTHON%" "%SCRIPT_DIR%oracle_schema_to_mysql.py" --all --drop
  exit /b %ERRORLEVEL%
)

if /I "%~1"=="resume-first-pension" (
  "%PYTHON%" "%SCRIPT_DIR%oracle_schema_to_mysql.py" --prefix FI_PN --prefix FI_XX --prefix FI_LA --prefix FI_PR --drop --resume
  exit /b %ERRORLEVEL%
)

if /I "%~1"=="resume-all" (
  "%PYTHON%" "%SCRIPT_DIR%oracle_schema_to_mysql.py" --all --drop --resume
  exit /b %ERRORLEVEL%
)

if /I "%~1"=="apply-fks" (
  "%PYTHON%" "%SCRIPT_DIR%oracle_schema_to_mysql.py" --apply-pending-fks
  exit /b %ERRORLEVEL%
)

if /I "%~1"=="list-first-pension" (
  "%PYTHON%" "%SCRIPT_DIR%oracle_schema_to_mysql.py" --prefix FI_PN --prefix FI_XX --prefix FI_LA --prefix FI_PR --list-only
  exit /b %ERRORLEVEL%
)

echo Usage:
echo   dump_oracle_schema.bat first-pension
echo   dump_oracle_schema.bat all
echo   dump_oracle_schema.bat resume-first-pension
echo   dump_oracle_schema.bat resume-all
echo   dump_oracle_schema.bat apply-fks
echo   dump_oracle_schema.bat list-first-pension
exit /b 1
