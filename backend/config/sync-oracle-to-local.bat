@echo off
setlocal
cd /d "%~dp0"
echo Replaced by: sync-oracle-to-finance-3307.bat
echo.
echo Step A = Oracle (koptfin) → MySQL finance :3307
echo Step B = finance → smpk_pension comes later.
echo.
call "%~dp0sync-oracle-to-finance-3307.bat"
