# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import copy_metadata

datas = [
    ("src/dockermcp", "dockermcp"),
    ("src/docker_mcp", "docker_mcp"),
    ("src/customization", "customization"),
    ("web_sota/dist", "web_sota/dist"),
    ("skills", "skills"),
]
for pkg in ("fastmcp", "fastapi", "uvicorn", "pydantic", "starlette", "prefab_ui", "httpx"):
    try:
        datas += copy_metadata(pkg)
    except Exception:
        pass

a = Analysis(
    ["run_server.py"],
    pathex=["src"],
    binaries=[],
    
    datas=datas,
    hiddenimports=[

    "_datetime",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.http.httptools_impl",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "docker_mcp.web",
        "docker_mcp.activity_log",
        "docker_mcp.llm.manager",
        "dockermcp.fleet_surface",
        "dockermcp.prefabs",
        "customization.server",
    "_strptime",
],
    hookspath=[],
    
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=True,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    
    name="docker-mcp-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
)





