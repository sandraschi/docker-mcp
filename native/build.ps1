#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "=== docker-mcp Tauri release build ===" -ForegroundColor Cyan

Write-Host "[1/3] web_sota (VITE_API_BASE for Tauri)" -ForegroundColor Yellow
Push-Location "$Root\web_sota"
try {
    $env:VITE_API_BASE = "http://127.0.0.1:10807"
    npm install
    npm run build
} finally { Pop-Location }

Write-Host "[2/3] PyInstaller sidecar" -ForegroundColor Yellow
pwsh -NoLogo -File "$Root\native\build-sidecar.ps1"

Write-Host "[3/3] Tauri bundle" -ForegroundColor Yellow
Push-Location "$Root\native"
try {
    $env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"
    npm install
    if (-not (Test-Path "icons\icon.ico")) {
        Write-Host "  Generating icons from web_sota/public/vite.svg" -ForegroundColor Gray
        npx @tauri-apps/cli icon "$Root\web_sota\public\vite.svg"
    }
    npx @tauri-apps/cli build
} finally { Pop-Location }

Write-Host "Done. Check native\target\release\bundle\" -ForegroundColor Green
