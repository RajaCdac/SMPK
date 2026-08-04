# Import a full smpk_pension dump into the Docker MySQL container (volume may already exist).
#
#   .\scripts\restore-mysql-docker.ps1 -SqlFile D:\backups\smpk_pension_full.sql
#
# Reads MYSQL_PASSWORD from .env in project root if -Password not given.

param(
    [Parameter(Mandatory = $true)]
    [string]$SqlFile,
    [string]$Password = "",
    [switch]$DropVolumeFirst
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path $PSScriptRoot -Parent
$envFile = Join-Path $projectRoot ".env"

if (-not (Test-Path $SqlFile)) {
    throw "SQL file not found: $SqlFile"
}

if (-not $Password -and (Test-Path $envFile)) {
    foreach ($line in Get-Content $envFile) {
        if ($line -match '^\s*MYSQL_PASSWORD\s*=\s*(.+)\s*$') {
            $Password = $Matches[1].Trim().Trim('"').Trim("'")
            break
        }
    }
}

if (-not $Password) {
    throw "Set MYSQL_PASSWORD in .env or pass -Password"
}

Push-Location $projectRoot
try {
    if ($DropVolumeFirst) {
        Write-Host "Stopping stack and removing MySQL volume..."
        docker compose down -v
        $initDir = Join-Path $projectRoot "docker\mysql\init"
        $target = Join-Path $initDir "01-smpk_pension.sql"
        if (-not (Test-Path $initDir)) {
            New-Item -ItemType Directory -Path $initDir -Force | Out-Null
        }
        Copy-Item -Path $SqlFile -Destination $target -Force
        Write-Host "Copied dump to $target — starting fresh import on first boot..."
        docker compose up -d --build
        Write-Host "Wait 1–3 minutes for MySQL init, then: docker compose logs -f mysql"
        return
    }

    Write-Host "Starting MySQL if needed..."
    docker compose up -d mysql
    Start-Sleep -Seconds 5

    Write-Host "Importing into smpk_pension (this may take several minutes)..."
    Get-Content -Path $SqlFile -Raw | docker compose exec -T mysql mysql -uroot "-p$Password" smpk_pension

    Write-Host "Restarting backend (runs migrate)..."
    docker compose up -d backend frontend

    Write-Host "Done. Open http://localhost and use your existing login from the dump."
}
finally {
    Pop-Location
}
