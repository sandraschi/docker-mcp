#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "=== docker-mcp sidecar build ===" -ForegroundColor Cyan
Push-Location $Root
try {
    $pi = uv run pyinstaller --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        uv pip install pyinstaller
    }
    Remove-Item -Recurse -Force "$Root\build\docker-mcp-backend" -ErrorAction SilentlyContinue
    Remove-Item -Force "$Root\dist\docker-mcp-backend.exe" -ErrorAction SilentlyContinue
    uv run pyinstaller docker-mcp-backend.spec --clean --noconfirm
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
    $triple = "x86_64-pc-windows-msvc"
    $src = "$Root\dist\docker-mcp-backend.exe"
    $dstDir = "$Root\native\binaries"
    $dst = "$dstDir\docker-mcp-backend-$triple.exe"
    if (-not (Test-Path $src)) { throw "Missing $src" }
    New-Item -ItemType Directory -Path $dstDir -Force | Out-Null
    Copy-Item $src $dst -Force
    Write-Host "Sidecar: $dst" -ForegroundColor Green
} finally {
    Pop-Location
}
