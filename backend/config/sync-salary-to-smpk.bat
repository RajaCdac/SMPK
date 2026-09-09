@echo off
setlocal EnableExtensions
cd /d "%~dp0"

REM ============================================================
REM  STEP B: Update smpk_pension (3306) from finance (3307)
REM  Default: INSERT IGNORE — new rows only (never update/delete local)
REM ============================================================

if not defined FINANCE_MYSQL_HOST set "FINANCE_MYSQL_HOST=localhost"
if not defined FINANCE_MYSQL_PORT set "FINANCE_MYSQL_PORT=3307"
if not defined FINANCE_MYSQL_USER set "FINANCE_MYSQL_USER=root"
if not defined FINANCE_MYSQL_PASSWORD set "FINANCE_MYSQL_PASSWORD=root123"
if not defined FINANCE_MYSQL_DATABASE set "FINANCE_MYSQL_DATABASE=finance"

if not defined TARGET_MYSQL_HOST set "TARGET_MYSQL_HOST=localhost"
if not defined TARGET_MYSQL_PORT set "TARGET_MYSQL_PORT=3306"
if not defined TARGET_MYSQL_USER set "TARGET_MYSQL_USER=root"
if not defined TARGET_MYSQL_PASSWORD set "TARGET_MYSQL_PASSWORD=root123"
if not defined TARGET_MYSQL_DATABASE set "TARGET_MYSQL_DATABASE=smpk_pension"

set "PY="
if exist "%~dp0..\venv\Scripts\python.exe" set "PY=%~dp0..\venv\Scripts\python.exe"
if not defined PY if exist "%~dp0venv\Scripts\python.exe" set "PY=%~dp0venv\Scripts\python.exe"
if not defined PY set "PY=python"

echo.
echo ============================================================
echo  finance:3307  -^>  smpk_pension:3306
echo  Mode: INSERT IGNORE (new rows only — local rows kept as-is)
echo ============================================================
echo  Source: %FINANCE_MYSQL_USER%@%FINANCE_MYSQL_HOST%:%FINANCE_MYSQL_PORT%/%FINANCE_MYSQL_DATABASE%
echo  Target: %TARGET_MYSQL_USER%@%TARGET_MYSQL_HOST%:%TARGET_MYSQL_PORT%/%TARGET_MYSQL_DATABASE%
echo.
echo  Example: bank table has 20 rows locally, 30 in finance
echo           -^> only the 10 new PKs are inserted
echo           -^> your existing 20 rows are NOT changed or deleted
echo.
echo  Options:
echo    1 = Salary tables only (ESR earn/dedn) — recommended
echo        fi_pr_th_salout, fi_pr_td_salout,
echo        fi_pm_mh_earndedn, fi_pn_mh_earndedn, fi_pr_mh_erndednmap
echo    2 = Full preferred pension table set + payroll (insert new only)
echo    3 = Dry-run salary tables only
echo    4 = Upsert mode (also refresh existing rows from finance)
echo    0 = Exit
echo.
set /p CHOICE=Enter choice [1]: 
if "%CHOICE%"=="" set "CHOICE=1"
if "%CHOICE%"=="0" goto :eof

cd /d "%~dp0scripts"

if "%CHOICE%"=="1" goto salary
if "%CHOICE%"=="2" goto full
if "%CHOICE%"=="3" goto dry
if "%CHOICE%"=="4" goto upsert
echo Invalid choice.
pause
exit /b 1

:salary
echo.
echo INSERT IGNORE salary / earn-dedn tables into smpk_pension ...
"%PY%" sync_finance_to_smpk.py --yes --insert-ignore --no-recreate ^
  --table fi_pr_th_salout ^
  --table fi_pr_td_salout ^
  --table fi_pm_mh_earndedn ^
  --table fi_pn_mh_earndedn ^
  --table fi_pr_mh_erndednmap
goto done

:full
echo.
echo INSERT IGNORE preferred tables + payroll into smpk_pension ...
"%PY%" sync_finance_to_smpk.py --yes --insert-ignore --no-recreate --include-payroll
goto done

:dry
echo.
"%PY%" sync_finance_to_smpk.py --dry-run --insert-ignore --no-recreate ^
  --table fi_pr_th_salout ^
  --table fi_pr_td_salout ^
  --table fi_pm_mh_earndedn ^
  --table fi_pn_mh_earndedn ^
  --table fi_pr_mh_erndednmap
goto done

:upsert
echo.
echo UPSERT (append) — new rows + refresh existing PKs from finance ...
"%PY%" sync_finance_to_smpk.py --yes --append --no-recreate --include-payroll
goto done

:done
if errorlevel 1 (
  echo.
  echo FAILED. Check finance:3307 has data and smpk_pension:3306 is up.
  pause
  exit /b 1
)
echo.
echo DONE. New rows inserted into smpk_pension (existing rows unchanged).
echo Restart backend if Docker is running, then re-open the screen you need.
pause
exit /b 0
