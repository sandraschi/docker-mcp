$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$RepoName = Split-Path -Leaf $Root
$Triple = "x86_64-pc-windows-msvc"
$ResourceDir = "$PSScriptRoot\resources"
$DevDir = "$PSScriptRoot\binaries"
New-Item -ItemType Directory -Force -Path $ResourceDir, $DevDir | Out-Null

Write-Host "=== ${RepoName} Tauri Release Build ===" -ForegroundColor Cyan

# Step 1: TypeScript lint gate + frontend build
$frontendDirs = @("web_sota", "webapp/frontend", "webapp")
foreach ($dir in $frontendDirs) {
    $frontend = Join-Path $Root $dir
    if (Test-Path "$frontend\package.json") {
        Write-Host "-> [1/4] Building frontend ($dir)..." -ForegroundColor Yellow
        Push-Location $frontend
        npm install --silent 2>$null

        Write-Host "  tsc --noEmit..." -ForegroundColor Gray
        $tscOut = npx tsc --noEmit 2>&1
        $tscExit = $LASTEXITCODE
        if ($tscExit -ne 0) {
            Write-Host "  TypeScript compilation FAILED - fix errors before building NSIS" -ForegroundColor Red
            Write-Host $tscOut
            throw "TypeScript compilation failed - fix all errors before building NSIS installer"
        }

        # Operator backend port (docker-mcp-native claim). Same value as backend.rs BACKEND_PORT
        # and tauri.conf.json; the backend-embedded dist must match the Tauri-served one.
        $env:VITE_API_BASE = "http://127.0.0.1:11240"
        npm run build
        if ($LASTEXITCODE -ne 0) { throw "Frontend build failed" }
        Pop-Location
        break
    }
}

# Step 2: PyInstaller backend (onefile)
Write-Host "-> [2/4] PyInstaller backend..." -ForegroundColor Yellow
$specFile = "$Root\${RepoName}-backend.spec"
if (Test-Path $specFile) {
    Push-Location $Root
    # Patch fastmcp to not crash on missing metadata (dist-info stripped below)
    $fm = "$Root\.venv\Lib\site-packages\fastmcp\__init__.py"
    if (Test-Path $fm) {
        $c = Get-Content $fm -Raw
        if ($c -match 'except PackageNotFoundError:\s+    __version__ = _version\("fastmcp"\)') {
            $c = $c -replace 'except PackageNotFoundError:\s+    __version__ = _version\("fastmcp"\)', 'except PackageNotFoundError:
    try:
        __version__ = _version("fastmcp")
    except PackageNotFoundError:
        __version__ = "0.0.0"'
            Set-Content $fm -Value $c -Encoding utf8
            Write-Host "  Patched fastmcp metadata fallback" -ForegroundColor Yellow
        }
    }
    # Project venv pyinstaller only: `uv run pyinstaller` can resolve to the global uv tool
    # env, which has none of the project deps and freezes a binary that crashes on import.
    $pyiExe = "$Root\.venv\Scripts\pyinstaller.exe"
    if (-not (Test-Path $pyiExe)) { throw "pyinstaller missing from project venv - run: uv add --dev pyinstaller pefile altgraph" }
    Get-Process -Name "docker-mcp-backend" -ErrorAction SilentlyContinue | Stop-Process -Force
    Remove-Item "$Root\dist\${RepoName}-backend.exe" -Force -ErrorAction SilentlyContinue
    & $pyiExe "$specFile" --clean --noconfirm
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }
    Pop-Location
} else {
    Write-Host "  WARNING: spec file not found at $specFile - using existing backend exe if present" -ForegroundColor DarkYellow
}

# Step 3: Embed in Tauri resources (+ dev fallback) with size gate + smoke test
Write-Host "-> [3/4] Embedding backend..." -ForegroundColor Yellow
$src = "$Root\dist\${RepoName}-backend.exe"
if (-not (Test-Path $src)) { throw "Backend exe not found at $src - PyInstaller step failed" }
$sizeMB = (Get-Item $src).Length / 1MB
if ($sizeMB -lt 5) {
    throw "Backend exe is only $([math]::Round($sizeMB, 1)) MB at $src - PyInstaller produced an empty/broken binary"
}
Write-Host "  Backend exe: $sizeMB MB"

# Bundle .env.example ONLY. The developer's real .env holds personal API keys and must never
# ship in the installer. tauri.conf.json lists resources/.env.example.
Remove-Item "$ResourceDir\.env" -Force -ErrorAction SilentlyContinue
$envExample = "$Root\.env.example"
if (Test-Path $envExample) {
    Copy-Item $envExample "$ResourceDir\.env.example" -Force
    Write-Host "  Bundled .env.example" -ForegroundColor Green
} else {
    throw ".env.example not found at repo root - tauri.conf.json bundles resources/.env.example"
}

Write-Host "  Smoke-testing frozen binary..." -ForegroundColor Yellow
$testPort = 11999
$oldPort = $env:MCP_PORT; $oldHost = $env:MCP_HOST
$env:MCP_PORT = "$testPort"; $env:MCP_HOST = "127.0.0.1"
$testProc = Start-Process -FilePath $src -NoNewWindow -PassThru -RedirectStandardError "$Root\dist\pyi-crash.log"
Start-Sleep -Seconds 15
$env:MCP_PORT = $oldPort; $env:MCP_HOST = $oldHost
if ($testProc.HasExited) {
    $crash = Get-Content "$Root\dist\pyi-crash.log" -Raw
    throw "Frozen binary crashed on launch (exit $($testProc.ExitCode)):`n$crash"
}
# Real endpoints, not just "process is alive": /health proves uvicorn is serving, the
# diagnostics route proves the tool/app modules imported inside the frozen binary.
foreach ($route in @("/api/health", "/api/v1/diagnostics")) {
    try {
        $resp = Invoke-WebRequest "http://127.0.0.1:$testPort$route" -UseBasicParsing -TimeoutSec 10
        if ($resp.StatusCode -ne 200) { throw "HTTP $($resp.StatusCode)" }
        Write-Host "  GET $route -> 200" -ForegroundColor Green
    } catch {
        $testProc.Kill()
        throw "Frozen binary smoke test: GET $route failed: $($_.Exception.Message)"
    }
}
$testProc.Kill(); $testProc.Dispose()
Remove-Item "$Root\dist\pyi-crash.log" -Force -ErrorAction SilentlyContinue
Write-Host "  Frozen binary smoke test PASSED" -ForegroundColor Green

Copy-Item $src "$ResourceDir\${RepoName}-backend.exe" -Force
Copy-Item $src "$DevDir\${RepoName}-backend-$Triple.exe" -Force

# Step 4: Single NSIS installer
Write-Host "-> [4/4] Tauri NSIS bundle..." -ForegroundColor Yellow
Push-Location $PSScriptRoot
$env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"
npx @tauri-apps/cli build --bundles nsis
if ($LASTEXITCODE -ne 0) { throw "Tauri build failed with exit code $LASTEXITCODE" }
Pop-Location

# Stage to repo dist/
$distDir = Join-Path $Root "dist"
New-Item -ItemType Directory -Force -Path $distDir | Out-Null
$nsisDir = "$PSScriptRoot\target\release\bundle\nsis"
if (Test-Path $nsisDir) { Copy-Item "$nsisDir\*-setup.exe" "$distDir\" -Force }
$strayExe = "$PSScriptRoot\target\release\docker-mcp-backend.exe"
if (Test-Path $strayExe) { Remove-Item $strayExe -Force; Write-Host "  Cleaned stray: $strayExe" -ForegroundColor DarkGray }

Write-Host "=== Build complete ===" -ForegroundColor Green
Write-Host "Ship: $nsisDir\*.exe"
