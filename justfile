name := "docker-mcp"
desc := "FastMCP 3.2 server for Docker operations"
ver := "3.2.0"

# Open the interactive recipe dashboard in the browser
default:
    @pwsh.exe -NoProfile -ExecutionPolicy Bypass -File ../mcp-central-docs/scripts/just-dashboard.ps1 -Path .

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
