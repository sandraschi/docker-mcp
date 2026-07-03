# Fleet Docker Compose Image Rebuild Plan

**Date:** 2026-06-23
**Problem:** Local Docker Desktop images are stale — containers run outdated code after source changes.

## Scope

95 compose files across 48 repos. Filtering to repos with **`build:` sections** (images built from local source, not pulled) that are **actively maintained**.

## Priority Tiers

### Tier 1 — Actively maintained, build from source, compose stale

These repos have compose files with `build:` sections, last modified weeks/months before their source code. Run `docker compose build` here first.

| Repo | Compose modified | Services to rebuild | Notes |
|------|-----------------|-------------------|-------|
| **docker-mcp** | 2026-02-09 | `dockermcp` | 4.5 months stale. Root compose. |
| **home-assistant-mcp** | 2026-02-09 | `home-assistant-mcp` | 4.5 months stale. |
| **monitoring-mcp** | 2026-02-09 | `monitoring-mcp` | 4.5 months stale. |
| **advanced-memory-mcp** | 2026-02-17 | `advanced-memory`, `webapp` | 4 months stale. |
| **handbrake-mcp** | 2025-09-23 | `handbrake-mcp` | **9 months stale.** |
| **osc-mcp** | 2026-01-16 | `osc-mcp` | 5 months stale. |
| **web-development-mcp** | 2026-01-25 | multi-stage builds | 5 months stale. |
| **vienna-life-assistant** | 2026-01-24 | `backend`, `celery-worker`, `celery-beat`, `frontend` | 5 months stale. |

### Tier 2 — Has compose with build, less stale

| Repo | Compose modified | Services to rebuild |
|------|-----------------|-------------------|
| **aiwatcher-mcp** | 2026-04-26 | `backend` |
| **avatar-mcp** | 2026-06-06 | `avatarmcp` |
| **blender-mcp** | 2026-05-28 | `blender-mcp` |
| **calibre-mcp** | 2026-06-07 | `backend`, `frontend` |
| **deepfang** | 2026-05-06 | `sanitizer`, `deepseek-bridge`, `worker`, `supervisor`, prom/grafana/loki |
| **devices-mcp** | 2026-06-20 | `app` |
| **games-app** | 2026-06-09 | `games-gateway`, `stockfish-engine`, `shogi-engine`, `go-engine` |
| **gimp-mcp** | 2026-05-30 | `gimp-mcp` |
| **google-ai-mcp** | 2026-06-20 | `backend`, `frontend` |
| **inkscape-mcp** | 2026-05-30 | `inkscape-mcp` |
| **mcp-federation-hub** | 2026-06-07 | `federation-bridge`, `federation-dashboard`, `federation-docs`, `worldlabs-mcp` |
| **meta_mcp** | 2026-05-19 | `frontend`, `backend` |
| **observability-mcp** | 2026-06-13 | `observability-mcp` |
| **resonite-mcp** | 2026-05-30 | `resonite-mcp` |
| **ring-mcp** | 2026-05-17 | `ring-mcp` |
| **sakana-mcp** | 2026-03-25 | `sakana-mcp`, `scientist-executor` (GPU) |
| **tailscale-mcp** | 2026-05-17 | `tailscale-mcp` |
| **unity3d-mcp** | 2026-05-30 | `unity3d-mcp` |

### Tier 3 — myai ecosystem (many sub-projects, individual control)

| Sub-project | Compose modified | Notes |
|------------|-----------------|-------|
| myai root | 2026-06-20 | 16+ services, most build from source |
| calibre_plus | 2026-02-03 | 3 services |
| bob_and_alice | 2026-04-05 | Ollama-dependent |
| teams_debate | 2025-11-13 | Inline ollama/lmstudio containers |
| immich_plus | 2026-02-09 | backend + frontend |
| voice_ai_suite | 2026-04-05 | backend + frontend |
| stablediff_gradio | 2026-02-02 | GPU container |
| wan_video_bridge | 2026-01-30 | GPU container |
| hunyuan_worldplay | 2026-01-30 | GPU container |

### Pull-only (no rebuild needed)

These compose files contain only `image:` references (no `build:` section). No source rebuild needed — just `docker compose pull` if versions are pinned:

`arr-mcp`, `mcp-central-docs/monitoring/`, `mcp-server-template`, `myconf/redis`, `mywienerlinien` (partial), `telephony-mcp`, `qbt-mcp`, `veogen` (partial), `external/*` repos

## Rebuild Strategy

### Quick win — bulk rebuild script

```powershell
# Run from fleet root. Rebuilds Tier 1 repos in parallel.
$tier1 = @(
    "docker-mcp",
    "home-assistant-mcp",
    "monitoring-mcp",
    "advanced-memory-mcp",
    "handbrake-mcp",
    "osc-mcp",
    "web-development-mcp",
    "vienna-life-assistant"
)

foreach ($repo in $tier1) {
    $compose = "D:\Dev\repos\$repo\docker-compose.yml"
    if (Test-Path $compose) {
        Write-Host "Building $repo..." -ForegroundColor Cyan
        Push-Location "D:\Dev\repos\$repo"
        docker compose build --pull 2>&1 | Out-Null
        Pop-Location
    }
}
```

### Per-repo commands

```powershell
# Standard rebuild with cache busting
cd D:\Dev\repos\<repo>
docker compose build --no-cache
docker compose up -d
```

### For GPU containers (sakana-mcp, myai stablediff/wan/hunyuan)

```powershell
docker compose build --no-cache
docker compose --profile gpu up -d
```

### For monitoring stacks (prometheus/grafana/loki)

These are pull-only when versions are pinned. Only rebuild if you changed the config:

```powershell
docker compose pull
docker compose up -d
```

## Verification

After rebuilding, verify each service:

```powershell
docker compose ps          # all services running?
docker compose logs --tail=20   # no crash loops?
# Health endpoint check (varies by repo)
curl http://localhost:<port>/health
```

## Mandatory: Dockerfile Audit Before Rebuild

**Canary lesson (handbrake-mcp, 2026-06-23):** Ancient compose files almost always have
stale Dockerfiles. Fix the Dockerfile first, then build.

### Pre-flight Dockerfile checklist

```powershell
# Check each of these before running 'docker compose build --no-cache'
# 1. Does the Dockerfile reference deleted directories?
rg "COPY " Dockerfile  # check every COPY path exists on disk

# 2. Fleet standard drift
rg "python:3\.(8|9|10|11)" Dockerfile  # should be 3.13
rg "pip install" Dockerfile             # should be 'uv sync'
rg "software-properties-common|add-apt-repository" Dockerfile  # Ubuntu-only, broken on Debian trixie (python:3.13-slim)
rg "^version:" docker-compose.yml  # obsolete in Compose v2 — delete the line

# 3. Multi-stage: does production stage have all it needs?
rg "COPY --from=builder /usr/local/bin/" Dockerfile  # uv binary must be copied for 'uv run' CMD

# 4. Does the Dockerfile still build? (quick test)
docker build --no-cache --target builder -t test-build . 2>&1 | tail -20
```

### Common failures found across the fleet

| Symptom | Cause | Fix |
|---------|-------|-----|
| `COPY dxt/ ./dxt/` fails | `dxt/` deleted, superseded by `mcpb/` | Remove the COPY line |
| `Unable to locate package software-properties-common` | PPA setup is Ubuntu-only; `python:3.13-slim` is Debian trixie | Install `handbrake-cli` directly from Debian repos |
| `fastmcp==3.2.0` installed instead of `3.4.x` | Old `requirements.txt` pins outdated version | Use `pyproject.toml` + `uv sync` |
| `noarchive=True` missing in `.spec` files | PyInstaller spec predates fleet standard | Add `noarchive=True` per tauri_nsis_building.md |
| `exec: "uv": executable file not found` | Production stage doesn't copy uv binary from builder | Add `COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv` before site-packages copy |
| `the attribute 'version' is obsolete` | `docker-compose.yml` still has `version: '3.8'` (Compose v1 artifact) | Remove the `version:` line entirely — Compose v2 ignores it |
| `fastmcp==3.2.0` instead of `3.4.x` | Old `uv.lock` pins outdated version from original scaffold | Run `uv sync --upgrade-package fastmcp` to bump |
| `pydantic_settings.exceptions.SettingsError` env var parse failure | `docker-compose.yml` sets `WATCH_FOLDERS=/app/watch` but pydantic model expects a list | Check env var types match pydantic model; use JSON arrays for list fields |
| Port 8000 used in compose mapping | Fleet policy forbids port 8000 (common dev conflict) | Map to a fleet port (10700-11000) — e.g. `"8000:8000"` → `"10700:8000"` |

## Run and Verify

After a successful build, always confirm the container actually starts and serves traffic:

```powershell
# 1. Start container in background
docker compose up -d <service-name>

# 2. Wait for health check (respects compose healthcheck interval)
Write-Host "Waiting for container to be healthy..." -NoNewline
for ($i = 0; $i -lt 30; $i++) {
    $status = docker inspect --format='{{json .State.Health.Status}}' $(docker compose ps -q <service-name>) 2>$null
    if ($status -eq '"healthy"') { Write-Host " OK"; break }
    Start-Sleep 2; Write-Host "." -NoNewline
}

# 3. Test the health endpoint directly
curl -f http://localhost:<port>/health
if ($LASTEXITCODE -eq 0) { Write-Host "Health check PASSED" } else { Write-Host "Health check FAILED" }

# 4. Check logs for errors
docker compose logs --tail=20 <service-name> | Select-String -Pattern "ERROR|Traceback|CRITICAL"

# 5. Clean up
docker compose down
```

### Just recipe pattern

Add to each repo's `justfile`:

```makefile
# Build, run, and verify the Docker container
docker-verify:
    Set-Location '{{justfile_directory()}}'
    docker compose build --no-cache
    docker compose up -d {{service}}
    Start-Sleep 10
    curl -f http://localhost:{{port}}/health
    if ($LASTEXITCODE -eq 0) { Write-Host "CONTAINER VERIFIED" -ForegroundColor Green }
    docker compose down
```

Call: `just docker-verify service=handbrake-mcp port=8000`

### Example: handbrake-mcp verification

```powershell
cd D:\Dev\repos\handbrake-mcp
docker compose up -d handbrake-mcp
# Wait for health (40s start_period + 30s interval x 3 retries)
curl -f http://localhost:8000/health
docker compose logs handbrake-mcp --tail=20
docker compose down
```

### When to skip Docker entirely

If the Dockerfile is too far gone, just run the MCP server directly:

```powershell
uv sync
uv run python src/server.py
```

## Critical: Docker Desktop Daemon Non-Responsive

Docker Desktop on Windows frequently hangs during compose builds, especially
`--no-cache` on large images. **Always run the pre-flight check before any rebuild:**

```powershell
docker info 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "DAEMON UNRESPONSIVE - recover first:" -ForegroundColor Red
    Write-Host "  taskkill /F /IM `"Docker Desktop.exe`" /T"
    exit 1
}
```

If the daemon hangs mid-build, use the **Triple Kill**:
```powershell
taskkill /F /IM "Docker Desktop.exe" /T
wsl --terminate docker-desktop
wsl --terminate docker-desktop-data
```

Then restart Docker Desktop, wait 90s, and retry. Full docs:
`mcp-central-docs/standards/docker-containerization.md` § Docker Desktop Daemon Reliability.

## Notes

- **14 repos** reference host apps (Blender, GIMP, Inkscape, etc.) — the compose builds the MCP bridge, not the host app itself. Rebuild when the MCP server code changes.
- **GPU repos** (`sakana-mcp`, `myai/stablediff-gradio`, `myai/wan-video-bridge`, `myai/hunyuan-worldplay`, `local-llm-mcp/vllm-*`) need `--gpus all` or `runtime: nvidia` in compose, and take longer to build.
- **deepfang** builds all its own containers (sanitizer, worker, bridge, supervisor, plus monitoring) from `containers/Dockerfile.*`. The prometheus/grafana/loki images here are `build:` too, not pulled — unusual.
- **external/** repos are third-party forks — only rebuild if you're actively developing them.
