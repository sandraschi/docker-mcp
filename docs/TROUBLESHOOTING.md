# Troubleshooting

## Web dashboard: HTTP 500

1. Confirm the API bridge is running on **10807** (backend PowerShell window from `start.ps1`).
2. Check `customization.server` exports `app` (`from server import web_app as app`).
3. `curl http://127.0.0.1:10807/api/health` should return `healthy`.

## MCPB install fails

- Rebuild from repo root: `just mcpb-pack` or `npx @anthropic-ai/mcpb pack . dist/docker-mcp-v3.3.0.mcpb`.
- Use root `manifest.json` and `assets/prompts/` (there is no `mcpb/` subfolder).
- Ensure `fastmcp>=3.3` in your environment matches `manifest.json`.

## Sampling / agentic workflow unavailable

- Start **Ollama** (11434) or **LM Studio** (1234).
- Set `DOCKER_MCP_SAMPLING_BASE_URL` if not using default Ollama.
- Use a client that supports MCP sampling (Cursor, Claude Desktop).

## Tauri build

- Run `native/ensure-sidecar-stub.ps1` before `cargo check` if sidecar is missing.
- Full release: `just build-native` (requires Rust toolchain).
- Webapp for Tauri must be built with `VITE_API_BASE=http://127.0.0.1:10807`.

## Docker daemon errors

- Verify Docker Desktop is running: `docker ps` in a terminal.
- On Windows, socket default: `//./pipe/docker_engine`.
- Dashboard **Recover Docker** (Overview quick actions) calls `POST /api/docker/recover` (triple-kill Desktop + backend + vpnkit).

## Virtualization support not detected (Windows)

Docker Desktop needs CPU virtualization from firmware. The classic trigger is a
crash or failed boot that resets the BIOS to defaults (seen 2026-09-27 on
Goliath: GSOD with no dump, then Docker, fTPM, and Secure Boot all broken at
once - full story in mcp-central-docs
`troubleshooting/2026-09-27_goliath-gsod-postmortem.md`).

Check from Windows (no reboot needed):

```powershell
Get-CimInstance Win32_Processor |
  Select-Object VirtualizationFirmwareEnabled, SecondLevelAddressTranslationExtensions
Get-ComputerInfo -Property HyperVRequirementVirtualizationFirmwareEnabled, HypervisorPresent
```

`VirtualizationFirmwareEnabled = False` means SVM (AMD) / VT-x (Intel) is off
in firmware. Fix:

1. Reboot into BIOS (Del/F2 on POST).
2. ASUS: Advanced > CPU Configuration > SVM Mode > Enabled.
   Intel boards: Advanced > CPU Configuration > Intel Virtualization Technology > Enabled.
3. While there, re-check anything else the reset took: fTPM (Firmware TPM) and
   Secure Boot (Windows UEFI mode) - both break Docker-adjacent tooling, games
   with anti-cheat, and Windows Hello.
4. Save, boot, re-run the check above - then `wsl --update` if WSL2 complains,
   and start Docker Desktop again.

Still failing with firmware enabled? Check Windows side:
`bcdedit /enum '{current}'` should show `hypervisorlaunchtype Auto`, and
Hyper-V / Virtual Machine Platform features must be on
(`OptionalFeatures.exe`).
