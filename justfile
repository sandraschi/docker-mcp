import 'scripts/just/fleet.just'

name := "docker-mcp"
desc := "FastMCP 3.5 server for Docker operations"
ver := "3.5.0"

# Open the interactive recipe dashboard in the browser
default:
    @just --list

# ── Build ─

# Sync Python dependencies
build:
    uv sync

# Build webapp
build-webapp:
    cd web_sota && npm install && npm run build

# MCPB bundle (Claude Desktop)
mcpb-pack:
    npx @anthropic-ai/mcpb pack . dist/docker-mcp-v{{ver}}.mcpb

# Tauri native installer (Windows release)
build-native:
    pwsh -NoLogo -File native/build.ps1

# Run CUA smoke test against installed NSIS app
cua-nsis-test:
    C:\Windows\py.exe scripts/cua-smoke.py

build-native-debug:
    Set-Location native
    $env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"
    npx @tauri-apps/cli build --debug

# ── Test ─

# Run test suite
test:
    uv run pytest tests/ -v

# Run tests with coverage
test-cov:
    uv run pytest tests/ --cov=src --cov-report=html

# ── Lint ─

# Run ruff (Python) + biome (webapp)
check:
    uv run ruff check .
    cd web_sota && npx @biomejs/biome ci .

# Auto-fix lint issues
fix:
    uv run ruff check . --fix
    uv run ruff format .
    cd web_sota && npx @biomejs/biome check --write .

# ── Docker ─

# Start the server
run:
    uv run docker-mcp

# Start webapp in dev mode
webapp-dev:
    cd web_sota && npm run dev

# Build Docker image
docker-build:
    docker build -t docker-mcp:latest .

# Docker compose up
up:
    docker compose up -d

# Docker compose down
down:
    docker compose down

# ── Housekeeping ─

# Clean build artifacts
clean:
    Remove-Item -Recurse -Force dist, build, .pytest_cache, .ruff_cache -ErrorAction SilentlyContinue

# View server logs
logs:
    Get-Content logs/dockermcp.log -Tail 50 -Wait
# ── Playwright E2E ─────────────────────────────────────────────────────

# Install Playwright browsers (one-time)
e2e-install:
    cd {{REPO}}\web_sota
    npx playwright install chromium

# Run Playwright E2E smoke tests (start backend first: just serve)
e2e:
    cd {{REPO}}\web_sota
    npx playwright test

