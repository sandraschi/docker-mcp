set windows-shell := ["pwsh.exe", "-NoLogo", "-Command"]

# ── Dashboard ─────────────────────────────────────────────────────────────────

# Display the SOTA Industrial Dashboard
default:
    @$lines = Get-Content '{{justfile()}}'; \
    Write-Host ' [SOTA] Industrial Operations Dashboard v1.3.2' -ForegroundColor White -BackgroundColor Cyan; \
    Write-Host '' ; \
    $currentCategory = ''; \
    foreach ($line in $lines) { \
        if ($line -match '^# ── ([^─]+) ─') { \
            $currentCategory = $matches[1].Trim(); \
            Write-Host "`n  $currentCategory" -ForegroundColor Cyan; \
            Write-Host ('  ' + ('─' * 45)) -ForegroundColor Gray; \
        } elseif ($line -match '^# ([^─].+)') { \
            $desc = $matches[1].Trim(); \
            $idx = [array]::IndexOf($lines, $line); \
            if ($idx -lt $lines.Count - 1) { \
                $nextLine = $lines[$idx + 1]; \
                if ($nextLine -match '^([a-z0-9-]+):') { \
                    $recipe = $matches[1]; \
                    $pad = ' ' * [math]::Max(2, (18 - $recipe.Length)); \
                    Write-Host "    $recipe" -ForegroundColor White -NoNewline; \
                    Write-Host "$pad$desc" -ForegroundColor Gray; \
                } \
            } \
        } \
    } \
    Write-Host "`n  [System State: PROD/HARDENED]" -ForegroundColor DarkGray; \
    Write-Host ''

# ── Quality ───────────────────────────────────────────────────────────────────

# Execute Ruff SOTA v13.1 linting
lint:
    Set-Location '{{justfile_directory()}}'
    uv run ruff check .
    Set-Location '{{justfile_directory()}}\web_sota'
    npx @biomejs/biome ci .

# Execute Ruff SOTA v13.1 fix and formatting
fix:
    Set-Location '{{justfile_directory()}}'
    uv run ruff check . --fix --unsafe-fixes
    uv run ruff format .
    Set-Location '{{justfile_directory()}}\web_sota'
    npx @biomejs/biome check --write .

# ── Hardening ─────────────────────────────────────────────────────────────────

# Execute Bandit security audit
check-sec:
    Set-Location '{{justfile_directory()}}'
    uv run bandit -r src/

# Execute safety audit of dependencies
audit-deps:
    Set-Location '{{justfile_directory()}}'
    uv run safety check

# justfile for docker-mcp

set shell := ["powershell.exe", "-NoProfile", "-Command"]

# Default help
# Development
dev:
    uv sync
    uv run docker-mcp

# Install dependencies
install:
    uv sync

# Run server
run:
    uv run docker-mcp

# Run webapp in dev mode
webapp-dev:
    cd web_sota
    npm install
    npm run dev

# Build webapp
webapp-build:
    cd web_sota
    npm install
    npm run build

# Run tests
test:
    uv run pytest tests/ -v

# Run tests with coverage
test-cov:
    uv run pytest tests/ --cov=src --cov-report=html

# Format code
fmt:
    uv run ruff format src/ tests/

# Lint code
# Type check
type-check:
    uv run pyright src/

# Check imports
check-imports:
    uv run python -m py_compile src/**/*.py

# Build Docker image
docker-build:
    docker build -t docker-mcp:latest .

# Run Docker image
docker-run:
    docker run -d \
      --name docker-mcp \
      -p 8000:8000 \
      -v /var/run/docker.sock:/var/run/docker.sock \
      docker-mcp:latest

# Docker compose up
docker-compose-up:
    docker compose up -d

# Docker compose down
docker-compose-down:
    docker compose down

# Docker compose monitoring stack
docker-monitoring:
    cd monitoring
    docker compose -f docker-compose-monitoring.yml up -d

# Package with mcpb
package:
    mcpb build

# Clean build artifacts
clean:
    rm -r dist/ build/ *.egg-info .pytest_cache .ruff_cache .mypy_cache

# View logs
logs:
    Get-Content logs/dockermcp.log -Tail 100 -Wait

# Help text
help:
    @echo "Docker MCP - FastMCP 3.1+ Server"
    @echo ""
    @echo "Available commands:"
    @echo "  just dev              - Run server with dependencies"
    @echo "  just install          - Install dependencies"
    @echo "  just run              - Run MCP server"
    @echo "  just test             - Run tests"
    @echo "  just lint             - Lint and format code"
    @echo "  just docker-build     - Build Docker image"
    @echo "  just docker-compose-up - Start docker-compose stack"
    @echo "  just webapp-dev       - Run webapp in dev mode"
    @echo "  just package          - Package with mcpb"
    @echo ""
