@echo off
setlocal EnableExtensions
cd /d "%~dp0"

REM ============================================================
REM  STEP A: Oracle FINANCE (SID koptfin) → MySQL finance :3307
REM  Default: APPEND / UPSERT (no DROP, no TRUNCATE)
REM ============================================================

if not defined ORACLE_DB_HOST set "ORACLE_DB_HOST=192.168.4.62"
if not defined ORACLE_DB_PORT set "ORACLE_DB_PORT=1521"
if not defined ORACLE_DB_SERVICE_NAME set "ORACLE_DB_SERVICE_NAME=koptfin"
if not defined ORACLE_DB_USER set "ORACLE_DB_USER=system"
if not defined ORACLE_DB_PASSWORD set "ORACLE_DB_PASSWORD=system"

if not defined MYSQL_HOST set "MYSQL_HOST=localhost"
if not defined MYSQL_PORT set "MYSQL_PORT=3307"
if not defined MYSQL_USER set "MYSQL_USER=root"
if not defined MYSQL_PASSWORD set "MYSQL_PASSWORD=root123"
if not defined MYSQL_DATABASE set "MYSQL_DATABASE=finance"

set "ORACLE_READ_ENABLED=True"

REM Absolute python path — relative path breaks after "cd scripts"
set "PY="
if exist "%~dp0..\venv\Scripts\python.exe" set "PY=%~dp0..\venv\Scripts\python.exe"
if not defined PY if exist "%~dp0venv\Scripts\python.exe" set "PY=%~dp0venv\Scripts\python.exe"
if not defined PY set "PY=python"

echo.
echo ============================================================
echo  Oracle → MySQL finance (port 3307)
echo  Mode   : APPEND / UPSERT  (no DROP, no TRUNCATE)
echo ============================================================
echo  Python : %PY%
echo  Oracle : %ORACLE_DB_USER%@%ORACLE_DB_HOST%:%ORACLE_DB_PORT%/%ORACLE_DB_SERVICE_NAME%
echo  MySQL  : %MYSQL_USER%@%MYSQL_HOST%:%MYSQL_PORT%/%MYSQL_DATABASE%
echo.
echo  Options:
echo    1 = Pension-related APPEND/UPSERT (recommended)
echo        FI_PN + FI_XX + FI_PR + FI_PM + FI_LA
echo    2 = Same as 1, RESUME
echo    3 = Pension-related INSERT IGNORE only
echo    4 = List tables only (connection test)
echo    5 = Test Oracle + MySQL connections only
echo    0 = Exit
echo.
set /p CHOICE=Enter choice [1]: 
if "%CHOICE%"=="" set "CHOICE=1"
if "%CHOICE%"=="0" goto :eof

if not exist "%PY%" if /I not "%PY%"=="python" (
  echo ERROR: Python not found: %PY%
  pause
  exit /b 1
)

cd /d "%~dp0scripts"
if errorlevel 1 (
  echo ERROR: cannot cd to scripts
  pause
  exit /b 1
)

if "%CHOICE%"=="1" goto dump_append
if "%CHOICE%"=="2" goto dump_resume
if "%CHOICE%"=="3" goto dump_ignore
if "%CHOICE%"=="4" goto list_only
if "%CHOICE%"=="5" goto test_conn
echo Invalid choice.
pause
exit /b 1

:dump_append
echo.
echo APPEND/UPSERT into existing finance tables (no truncate/drop) ...
"%PY%" oracle_schema_to_mysql.py --prefix FI_PN --prefix FI_XX --prefix FI_PR --prefix FI_PM --prefix FI_LA --append
goto done

:dump_resume
echo.
echo Resuming APPEND/UPSERT ...
"%PY%" oracle_schema_to_mysql.py --prefix FI_PN --prefix FI_XX --prefix FI_PR --prefix FI_PM --prefix FI_LA --append --resume
goto done

:dump_ignore
echo.
echo INSERT IGNORE only (new rows only) ...
"%PY%" oracle_schema_to_mysql.py --prefix FI_PN --prefix FI_XX --prefix FI_PR --prefix FI_PM --prefix FI_LA --insert-ignore
goto done

:list_only
echo.
"%PY%" oracle_schema_to_mysql.py --prefix FI_PN --prefix FI_XX --prefix FI_PR --prefix FI_PM --prefix FI_LA --list-only
goto done

:test_conn
echo.
echo Testing Oracle connection...
"%PY%" -c "from oracle_table_to_mysql import connect_oracle, ORACLE_DEFAULTS; c=connect_oracle(); print('Oracle OK', ORACLE_DEFAULTS['service_name']); c.close()"
if errorlevel 1 goto done
echo Testing MySQL finance:3307...
"%PY%" -c "from oracle_table_to_mysql import connect_mysql, public_mysql_config; c=connect_mysql(create_db=True); print('MySQL OK', public_mysql_config()); c.close()"
goto done

:done
set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" (
  echo.
  echo FAILED with exit code %EC%.
  echo Scroll up for the real Python/Oracle/MySQL error message.
  echo Logs (if any): %~dp0scripts\dump_logs\
  echo.
  echo Quick checks:
  echo   - Run this bat again and choose 5 (connection test)
  echo   - Confirm MySQL finance is on port 3307
  echo   - Confirm Oracle SID/service is koptfin
  pause
  exit /b %EC%
)

echo.
echo DONE.
pause
exit /b 0
