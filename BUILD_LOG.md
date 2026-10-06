# Build log

Running record of installer / bundle builds, failures, and fixes.

## 2026-10-06 (later) - dual transport, stdout fix, release assets

Rebuilt both artifacts and replaced the assets on the `v3.5.0` release
(`docker-mcp-3.5.0.mcpb`, `docker-mcp-3.5.0-setup.exe`). The release had no assets before.

| # | Problem | Fix |
|---|---------|-----|
| 1 | **JSON log lines went to stdout in stdio mode**, corrupting the MCP JSON-RPC stream. This also affected the `.mcpb` shipped earlier the same day. | `logging_config.py` console handler writes to stderr. |
| 2 | Sidecar `run_server.py` was HTTP-only, so the installed `docker-mcp-backend.exe` could not be registered in an IDE over stdio. | Same contract as arxiv-mcp: HTTP by default (Tauri spawn), stdio on `--stdio` or `MCP_TRANSPORT=stdio`, without the web bridge on 10807 (`dockermcp.server.main(web_bridge=False)`). |
| 3 | No test proved the server speaks MCP over stdio; the earlier launch checks only showed a process staying alive. | `scripts/smoke_stdio.py` does a real `initialize` + `tools/list` handshake and fails on any non-JSON-RPC stdout. `native/build.ps1` runs it against the frozen exe; verified against the packed `.mcpb` from a clean unpack (43 tools). |
| 4 | Packed `.mcpb` included two stale `pyproject.toml.bak_*` files. | `*.bak*` added to `.mcpbignore`. |

Not done: CUA install/launch/uninstall smoke test. The release tag `v3.5.0` still points at an older commit than these binaries.

## 2026-10-06 - v3.5.0 rebuild (MCPB + Tauri NSIS)

Artifacts:

| Artifact | Path | Size |
|----------|------|------|
| NSIS installer | `dist/Docker MCP_3.5.0_x64-setup.exe` | 39.7 MB |
| Frozen backend (embedded) | `dist/docker-mcp-backend.exe` | 35.5 MB |
| MCPB | `dist/schip-mcp-docker-v3.5.0.mcpb` | 258 KB |

Gates passed: ruff, tsc, biome ci, PyInstaller frozen-binary smoke (`GET /api/health` and
`GET /api/v1/diagnostics` both 200), MCPB import-isolation / AST / pollution / launch checks.
Not run: CUA install/launch/uninstall smoke test (`just cua-nsis-test`).

### Problems found in the Phase 1 audit and fixed before building

| # | Problem | Fix |
|---|---------|-----|
| 1 | `native/build.ps1` copied the developer's real `.env` into `resources/` and the installer. Leaks personal API keys to every user. | Bundle `.env.example` only; build fails if it is missing. |
| 2 | `build.ps1` ran `uv run pyinstaller`, which can resolve to the global uv tool env and freeze a backend with no project deps. | Use `.venv\Scripts\pyinstaller.exe`; pre-kill orphan backend and remove stale exe. |
| 3 | `native/src/main.rs` had its own `start_backend` that spawned the child directly: no `free_port`, no `PORT` env, no health poll. The audited `backend.rs::spawn_backend` was dead code. | `start_backend` now calls `spawn_backend`. Child killed on `Exit` and `ExitRequested`. |
| 4 | `backend.rs::free_port` was a single `taskkill` by port with a 500 ms sleep. | Multi-layer kill (image name, port, UAC escalation), self-PID excluded, polls up to 240 s. Added a 30x2 s TCP health loop. |
| 5 | Operator backend used the dev backend port 10807 (side-by-side rule). | Claimed `docker-mcp-native` (frontend 11239, backend 11240) via `fleet-gate/claim_ports.py`. Backend port set in `backend.rs`, `tauri.conf.json` (`VITE_API_BASE` + CSP), `build.ps1`, `scripts/cua-nsis-config.json`. `web_sota/src/lib/api.ts` is now `VITE_API_BASE`-driven (dev default 10807). |
| 6 | Spec missed `joserfc` / `cachetools` hiddenimports; `run_server.py` missed `_datetime` / `mcp.types` eager imports. | Added. |
| 7 | `mcpb/run_server.py` was the Tauri HTTP sidecar launcher (`--http` required), so the MCPB could not serve Claude Desktop over stdio and failed the import-isolation check. | Now a stdio launcher for `dockermcp.server:main`. |
| 8 | `dockermcp.mcp_instance` imports sibling package `docker_mcp`; `mcpb/pack.ps1` staged only `dockermcp`. | `pack.ps1` stages `docker_mcp` too. |
| 9 | Pre-existing: ruff S310 (`file:` URLs reachable in `web_queries.py` HTTP helpers) and biome format/import-order errors blocked the pre-commit hook. | http(s) scheme guard; biome safe fixes. |

### Known leftovers

- `mcpb/pyproject.toml.bak_20260827_*` are packed into the .mcpb (add `*.bak*` to `.mcpbignore`).
- `mcpb/pyproject.toml` still says name `schip-mcp-docker`, version 3.3.0; manifest says 3.5.0.
- 3-4-100 prompt check fails (non-blocking): `examples.json` has no entries.
- The stdio server (`dockermcp.server.main`) still starts its FastAPI bridge on 10807 in a thread.
