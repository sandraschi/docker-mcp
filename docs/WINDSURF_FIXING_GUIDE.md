# Windsurf Fixing Guide for Docker MCP Server

## CRITICAL JSON-RPC Protocol Fix

**Problem**: Server outputs plain text warnings to stdout instead of JSON, breaking Claude communication.

**Root Cause**: Import errors and stdout pollution cause "Warning: F..." messages that corrupt JSON-RPC protocol.

## FastMCP 2.11.3 REQUIREMENTS - DO NOT DOWNGRADE

Sandra INSISTS on FastMCP 2.11.3. Use these CORRECT patterns:

### 1. TOOL DECORATOR SYNTAX - CRITICAL RULES

❌ **NEVER DO THIS** (breaks Python parsing):
```python
@mcp.tool(
    """This is wrong and breaks everything"""
)
def my_tool():
    """Docstring goes HERE, not in decorator"""
    pass
```

✅ **CORRECT FastMCP 2.11.3 patterns**:
```python
@mcp.tool(
    name="list_containers", 
    description="List Docker containers with status"
)
def list_containers(all_states: bool = True) -> Dict[str, Any]:
    """Proper docstring placement - INSIDE function body."""
    # Implementation here
```

### 2. LOGGING CONFIGURATION - FIX STDOUT POLLUTION

❌ **Current broken logging** (sends warnings to stdout):
```python
logging.basicConfig(level=logging.INFO)  # Goes to stdout - BREAKS JSON-RPC
```

✅ **FIXED logging** (stderr only):
```python
import sys
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]  # CRITICAL: stderr not stdout
)
```

### 3. IMPORT STRUCTURE FIXES

Current server.py has broken imports causing warnings. Fix these:

❌ **Broken imports causing stdout warnings**:
```python
from .json_encoder import dumps as custom_dumps  # Missing file
from docker_ops.containers import ContainerManager  # Wrong structure  
from dockermcp.tools.containers import list_containers  # Circular import
```

✅ **Clean import structure**:
```python
import docker
from fastmcp import FastMCP
from pydantic import BaseModel, Field
# Import only what actually exists and works
```

### 4. TOOL REGISTRATION - CORRECT 2.11.3 PATTERNS

❌ **Duplicate registrations causing conflicts**:
```python
# Don't do both of these:
@mcp.tool(name="list_containers")  # Decorator registration
def list_containers(): pass

mcp.tool(list_containers)  # Manual registration - CONFLICT
```

✅ **Pick ONE registration method**:
```python
@mcp.tool(name="list_containers", description="List containers")
def list_containers() -> Dict[str, Any]:
    """Implementation with proper return typing."""
    pass
```

### 5. SERVER STARTUP - PREVENT WARNINGS

❌ **Current main() allows import warnings to stdout**:
```python
def main():
    logger.info("Starting...")  # If logger goes to stdout = BROKEN
    mcp.run()
```

✅ **Clean startup with stderr logging**:
```python
def main():
    # Verify Docker BEFORE any imports that might warn
    try:
        docker_client = docker.from_env()
        docker_client.ping()
    except Exception as e:
        print(f"Docker unavailable: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Now safe to start MCP
    mcp.run()
```

## FIXING STEPS FOR WINDSURF

1. **Fix logging first** - Replace all logging config with stderr-only version
2. **Remove broken imports** - Comment out all imports that don't exist
3. **Clean tool definitions** - Remove duplicate @mcp.tool + mcp.tool() registrations  
4. **Fix decorator syntax** - Never put """ inside @mcp.tool() decorators
5. **Use Docker client directly** - Skip the broken manager classes for now
6. **Test minimal version** - Start with just list_containers working

## CORRECT FILE STRUCTURE

Use this clean server.py structure:

```python
#!/usr/bin/env python3
import sys
import logging
import docker
from fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import Dict, Any

# CRITICAL: Logging to stderr only
logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stderr)]
)

# CRITICAL: Test Docker connection early
docker_client = docker.from_env()
mcp = FastMCP("docker-mcp")

@mcp.tool(name="list_containers", description="List Docker containers")
def list_containers(all_states: bool = True) -> Dict[str, Any]:
    """List containers using docker client directly."""
    containers = docker_client.containers.list(all=all_states)
    return {"success": True, "containers": [c.name for c in containers]}

if __name__ == "__main__":
    mcp.run()
```

## NEVER DO THESE THINGS

1. **Never** put docstrings inside @mcp.tool() decorators
2. **Never** log to stdout (breaks JSON-RPC)  
3. **Never** import modules that don't exist
4. **Never** register tools twice (decorator + manual)
5. **Never** downgrade from FastMCP 2.11.3

## TESTING

After fixes, test with:
```bash
cd D:\Dev\repos\dockermcp\src
python server.py
```

Should start cleanly without warnings. If you see "Warning:" messages, logging is still going to stdout.

## SUCCESS CRITERIA

- ✅ No stdout warnings during startup
- ✅ Only JSON responses to Claude
- ✅ FastMCP 2.11.3 patterns used correctly
- ✅ Clean tool decorator syntax
- ✅ Proper logging to stderr only
