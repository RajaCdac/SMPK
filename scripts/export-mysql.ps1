# Export full smpk_pension database (run on the machine that has your current MySQL data).
#
# Examples:
#   .\scripts\export-mysql.ps1
#   .\scripts\export-mysql.ps1 -DbHost 192.168.4.102 -User root -Password secret
#   .\scripts\export-mysql.ps1 -OutFile D:\backups\smpk_pension_full.sql

param(
    [string]$DbHost = "127.0.0.1",
    [int]$Port = 3306,
    [string]$User = "root",
    [string]$Password = "",
    [string]$Database = "smpk_pension",
    [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path $PSScriptRoot -Parent
if (-not $OutFile) {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $OutFile = Join-Path $projectRoot "backups\smpk_pension_full_$stamp.sql"
}

$outDir = Split-Path $OutFile -Parent
if (-not (Test-Path $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}

$mysqldump = Get-Command mysqldump -ErrorAction SilentlyContinue
if (-not $mysqldump) {
    Write-Host "mysqldump not in PATH. Use SQLyog: Database -> Export -> Export database '$Database' -> SQL file."
    Write-Host "Save as: $OutFile"
    exit 1
}

$args = @(
    "-h", $DbHost,
    "-P", $Port.ToString(),
    "-u", $User,
    "--single-transaction",
    "--routines",
    "--triggers",
    "--set-gtid-purged=OFF",
    $Database
)

if ($Password) {
    $env:MYSQL_PWD = $Password
}

Write-Host "Exporting $Database from ${DbHost}:${Port} -> $OutFile"
& mysqldump @args | Set-Content -Path $OutFile -Encoding utf8
Remove-Item Env:MYSQL_PWD -ErrorAction SilentlyContinue

Write-Host "Done. Size: $((Get-Item $OutFile).Length / 1MB) MB"
Write-Host ""
Write-Host "Docker first-time import:"
Write-Host "  Copy to: $projectRoot\docker\mysql\init\01-smpk_pension.sql"
Write-Host "  docker compose down -v"
Write-Host "  docker compose up -d --build"
