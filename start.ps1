# *********************************************************************************
# * SOTA Fleet Orchestration - Standardized Start System (v1.19.0)                *
# * Generated/Repaired by Antigravity on 2026-09-27                  *
# *********************************************************************************

param(
    [switch]$Headless,
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$NoBrowser
)
$child = Join-Path $PSScriptRoot "web_sota/start.ps1"
if (-not (Test-Path -LiteralPath $child)) {
    Write-Error "Missing launcher: $child"
    exit 1
}
& $child @PSBoundParameters
exit $LASTEXITCODE



# --- SOTA PORT SAFETY START ---
# Ports live in fleet-start.config.ps1 (no $Port var in this file).
foreach ($portNum in @(10807, 10806)) {
    Get-NetTCPConnection -LocalPort $portNum -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
        if ($_.OwningProcess -ne $PID) {
            Write-Host "Clearing stale listener on port $portNum (PID $($_.OwningProcess))..." -ForegroundColor Yellow
            Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
}
Start-Sleep -Seconds 1
# --- SOTA PORT SAFETY END ---
