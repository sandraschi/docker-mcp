name := "docker-mcp"
desc := "FastMCP 3.2 server for Docker operations"
ver := "3.2.0"

default:
    @powershell -NoLogo -Command " \
        $lines = Get-Content '{{justfile()}}'; \
        Write-Host ' [{{name}}] {{desc}} v{{ver}}' -ForegroundColor White -BackgroundColor Cyan; \
        Write-Host '' ; \
        $currentCategory = ''; \
        foreach ($line in $lines) { \
            if ($line -match '^# ── ([^─]+) ─') { \
                $currentCategory = $matches[1].Trim(); \
                Write-Host \"`n  $currentCategory\" -ForegroundColor Cyan; \
                Write-Host '  ' + ('─' * 45) -ForegroundColor Gray; \
            } elseif ($line -match '^# ([^─].+)') { \
                $desc = $matches[1].Trim(); \
                $idx = [array]::IndexOf($lines, $line); \
                if ($idx -lt $lines.Count - 1) { \
                    $nextLine = $lines[$idx + 1]; \
                    if ($nextLine -match '^([a-z0-9-]+)(\*)?:') { \
                        $recipe = $matches[1]; \
                        $pad = ' ' * [math]::Max(2, (18 - $recipe.Length)); \
                        Write-Host \"    $recipe\" -ForegroundColor White -NoNewline; \
                        Write-Host \"$pad$desc\" -ForegroundColor Gray; \
                    } \
                } \
            } \
        } \
        Write-Host ''"

# ── Build ─

# Sync Python dependencies
build:
    uv sync

# Build webapp
build-webapp:
    cd web_sota && npm ci && npm run build

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
