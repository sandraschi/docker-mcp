# Docker MCP Resilience Fix Guide

**Created**: 2025-09-11 23:28  
**Project**: docker-mcp  
**Status**: CRITICAL FIX REQUIRED  
**Priority**: URGENT - MCP currently crashes if Docker not available

## Problem Summary

Docker MCP has a critical design flaw where it performs a hard crash on startup if the Docker daemon is not available. This makes the MCP completely unusable in environments where Docker might not always be running.

### Current Failure Pattern
```python
# File: src/dockermcp/__init__.py:57
docker_client = docker.from_env()  # ❌ CRASHES ENTIRE MCP IF DOCKER DOWN
```

**Error**: `docker.errors.DockerException: Error while fetching server API version`  
**Result**: MCP server terminates, Claude loses connection

## Required Fixes (Priority Order)

### 1. CRITICAL - Graceful Docker Connection (Immediate)

**File**: `src/dockermcp/__init__.py`

Replace hard crash pattern with graceful handling:

```python
# Current (BROKEN):
docker_client = docker.from_env()

# Fixed version:
try:
    docker_client = docker.from_env()
    docker_available = True
    docker_error = None
    logger.info("Docker daemon connected successfully")
except Exception as e:
    docker_client = None
    docker_available = False
    docker_error = str(e)
    logger.warning(f"Docker daemon not available: {e}")
```

### 2. HIGH - Add Docker Status Tool

**File**: `src/dockermcp/tools/docker_status.py` (NEW FILE)

```python
@tool
async def docker_status() -> str:
    """Get Docker daemon status and connectivity information."""
    status = {
        "docker_available": docker_available,
        "error": docker_error if not docker_available else None,
        "version": None,
        "connection_type": "named_pipes" if sys.platform == "win32" else "socket"
    }
    
    if docker_available and docker_client:
        try:
            version_info = docker_client.version()
            status["version"] = version_info.get("Version", "unknown")
            status["api_version"] = version_info.get("ApiVersion", "unknown")
        except Exception as e:
            status["version_error"] = str(e)
    
    # Add Windows-specific Docker service status
    if sys.platform == "win32":
        status["service_status"] = check_docker_service_windows()
    
    return json.dumps(status, indent=2)

def check_docker_service_windows():
    """Check Docker service status on Windows."""
    try:
        import subprocess
        result = subprocess.run(['sc', 'query', 'Docker Desktop Service'], 
                               capture_output=True, text=True)
        if "RUNNING" in result.stdout:
            return "running"
        elif "STOPPED" in result.stdout:
            return "stopped"
        else:
            return "unknown"
    except Exception:
        return "check_failed"
```

### 3. HIGH - Tool-Level Error Handling

**Apply to ALL Docker tools** in `src/dockermcp/tools/`:

```python
def check_docker_available(func):
    """Decorator to check Docker availability before tool execution."""
    def wrapper(*args, **kwargs):
        if not docker_available:
            return f"❌ Docker daemon not available: {docker_error}\n\n" \
                   f"💡 Troubleshooting:\n" \
                   f"1. Start Docker Desktop\n" \
                   f"2. Run 'docker version' to test\n" \
                   f"3. Use docker_status tool for diagnostics"
        try:
            return func(*args, **kwargs)
        except docker.errors.DockerException as e:
            return f"❌ Docker operation failed: {str(e)}"
    return wrapper

# Apply to all tools:
@tool
@check_docker_available
async def list_containers() -> str:
    # existing implementation
```

### 4. MEDIUM - Dynamic Reconnection

**File**: `src/dockermcp/tools/docker_reconnect.py` (NEW FILE)

```python
@tool
async def docker_reconnect() -> str:
    """Attempt to reconnect to Docker daemon."""
    global docker_client, docker_available, docker_error
    
    try:
        docker_client = docker.from_env()
        docker_available = True
        docker_error = None
        
        # Test connection
        version = docker_client.version()
        return f"✅ Docker reconnected successfully!\n" \
               f"Version: {version.get('Version', 'unknown')}\n" \
               f"API Version: {version.get('ApiVersion', 'unknown')}"
    
    except Exception as e:
        docker_error = str(e)
        return f"❌ Reconnection failed: {docker_error}\n\n" \
               f"💡 Please ensure Docker Desktop is running"
```

## Implementation Steps for Windsurf

### Step 1: Update __init__.py (URGENT)
```bash
# Edit src/dockermcp/__init__.py
# Replace line ~57 with graceful connection handling
# Add global variables for connection state
```

### Step 2: Create Status Tool
```bash
# Create src/dockermcp/tools/docker_status.py
# Import in __init__.py tools list
# Test with: docker_status tool call
```

### Step 3: Add Error Handling Decorator
```bash
# Create decorator function in __init__.py
# Apply @check_docker_available to all existing tools
# Test all tools work with Docker down
```

### Step 4: Create Reconnect Tool
```bash
# Create src/dockermcp/tools/docker_reconnect.py  
# Test reconnection workflow
```

### Step 5: Update Tool Imports
```bash
# Edit src/dockermcp/__init__.py
# Add new tools to TOOLS list:
# - docker_status
# - docker_reconnect
```

## Testing Strategy

### Test Case 1: Docker Down on Startup
1. Stop Docker Desktop
2. Start MCP server
3. Verify: MCP starts successfully (no crash)
4. Call docker_status tool
5. Verify: Shows Docker unavailable with diagnostic info

### Test Case 2: Docker Down During Operation
1. Start MCP with Docker running
2. Stop Docker Desktop  
3. Call any Docker tool
4. Verify: Graceful error message, not crash

### Test Case 3: Docker Reconnection
1. Start MCP with Docker down
2. Start Docker Desktop
3. Call docker_reconnect tool
4. Verify: Docker tools now work

## Files to Modify

### Existing Files
- `src/dockermcp/__init__.py` - Graceful connection + decorator
- All files in `src/dockermcp/tools/` - Add error handling decorator

### New Files  
- `src/dockermcp/tools/docker_status.py` - Status diagnostics
- `src/dockermcp/tools/docker_reconnect.py` - Dynamic reconnection

## Success Criteria

✅ **MCP starts successfully even when Docker is down**  
✅ **All tools provide helpful error messages instead of crashing**  
✅ **Status tool provides comprehensive diagnostics**  
✅ **Reconnection tool allows recovery without MCP restart**  
✅ **No JSON-RPC protocol corruption from error logging**

## Notes for Windsurf Development

- This is a **critical reliability fix** - current MCP is unusable in many environments
- Focus on **graceful degradation** - partial functionality is better than total crash
- **Test thoroughly** with Docker in various states (down, starting, running, stopping)
- **Error messages should be user-friendly** with actionable troubleshooting steps
- Consider this a **foundational fix** for Docker MCP reliability

---
**Next Action**: Start with Step 1 (graceful connection in __init__.py) as this is blocking all other functionality.
