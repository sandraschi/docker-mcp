# DockerMCP Windsurf Improvement Guide

**Guide Version:** 1.0  
**Target Audience:** Sandra + AI development team  
**Estimated Implementation Time:** 2-3 weeks  
**Priority Level:** CRITICAL (Repository currently non-functional)

## Quick Start: Fix Critical Issues (Day 1)

### 1. Make the Server Runnable

**Problem**: ImportError on 8 missing modules  
**Solution**: Create stub modules or remove imports

#### Option A: Create Stub Modules (Recommended)
```powershell
# Create missing module structure
New-Item -ItemType Directory -Force -Path "D:\Dev\repos\dockermcp\src\docker_ops"
New-Item -ItemType Directory -Force -Path "D:\Dev\repos\dockermcp\src\workflow_intel"

# Create stub files
@"
class NetworkManager:
    def __init__(self):
        pass
    
    def list_networks(self):
        return {"success": False, "error": "Not implemented yet"}
"@ | Out-File -FilePath "D:\Dev\repos\dockermcp\src\docker_ops\networks.py" -Encoding UTF8

@"
class VolumeManager:
    def __init__(self):
        pass
    
    def list_volumes(self):
        return {"success": False, "error": "Not implemented yet"}
"@ | Out-File -FilePath "D:\Dev\repos\dockermcp\src\docker_ops\volumes.py" -Encoding UTF8
```

#### Complete Stub Creation Script
```powershell
# Run this in dockermcp root directory
cd "D:\Dev\repos\dockermcp"

# Create all missing modules with basic stubs
$modules = @(
    "src\docker_ops\networks.py",
    "src\docker_ops\volumes.py", 
    "src\docker_ops\system.py",
    "src\workflow_intel\stack_health.py",
    "src\workflow_intel\problem_detection.py",
    "src\workflow_intel\automation.py",
    "src\workflow_intel\vienna_specific.py"
)

foreach ($module in $modules) {
    $className = (Split-Path $module -LeafBase | ForEach-Object { (Get-Culture).TextInfo.ToTitleCase($_) }) + "Manager"
    if ($module -like "*workflow_intel*") {
        $className = switch (Split-Path $module -LeafBase) {
            "stack_health" { "StackHealthChecker" }
            "problem_detection" { "ProblemDetector" } 
            "automation" { "AutomationManager" }
            "vienna_specific" { "ViennaEnvironment" }
        }
    }
    
    @"
class $className:
    def __init__(self):
        pass
    
    def placeholder_method(self):
        return {"success": False, "error": "Not implemented yet"}
"@ | Out-File -FilePath $module -Encoding UTF8
}

# Test the server
python -m src.server
```

### 2. Basic FastMCP 2.10 Integration

**Problem**: Using subprocess instead of FastMCP  
**Solution**: Wrap existing functions with FastMCP decorators

```python
# Add to server.py after imports
from fastmcp import FastMCP

app = FastMCP("DockerMCP")

# Convert existing functions to MCP tools
@app.tool()
def list_containers(all_states: bool = True) -> dict:
    """List Docker containers with status information."""
    container_mgr = ContainerManager()
    return container_mgr.list_containers(all_states)

@app.tool() 
def get_container_info(container_name: str) -> dict:
    """Get detailed information about a specific container."""
    container_mgr = ContainerManager()
    return container_mgr.get_container_info(container_name)

# Update main() function
def main():
    app.run()
```

## Windsurf Configuration Optimization

### 1. Streamline Rules (HIGH PRIORITY)

**Current Problem**: 32KB generic rules file  
**Solution**: Create dockermcp-specific rules

<function_calls>
<invoke name="filesystem:write_file">
<parameter name="content"># DockerMCP Windsurf Rules - Austrian Efficiency Edition

**Version:** 1.0  
**Last Updated:** 2025-08-13  
**Project:** dockermcp  

## Core Development Rules

### 1. FastMCP 2.10 Patterns

#### Tool Function Structure
```python
@app.tool()
def operation_name(param: type) -> Dict[str, Any]:
    """
    Clear description of what this does.
    
    Args:
        param: Description of parameter
        
    Returns:
        Standardized result dictionary
    """
    try:
        # Implementation
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

#### Error Handling Pattern
```python
# Always return structured responses
def docker_operation():
    try:
        result = subprocess.run(['docker', 'command'], capture_output=True, text=True)
        if result.returncode == 0:
            return {"success": True, "data": result.stdout}
        else:
            return {"success": False, "error": result.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### 2. Docker Command Patterns

#### Safe Docker Execution
```python
# Always use timeout and error handling
def run_docker_command(args: List[str], timeout: int = 30):
    cmd = ["docker"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "command": " ".join(cmd)
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Command timed out after {timeout}s"}
```

#### JSON Output Parsing
```python
# Docker JSON format parsing
def parse_docker_json(output: str):
    items = []
    for line in output.split('\n'):
        if line.strip():
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return items
```

### 3. Austrian Efficiency Patterns

#### Vienna Stack Definitions
```python
VIENNA_STACKS = {
    "veogen": {
        "containers": ["veogen-backend", "veogen-redis", "veogen-postgres"],
        "health_check": "http://localhost:8000/health",
        "restart_order": ["postgres", "redis", "backend"]
    },
    "immich": {
        "containers": ["immich-server", "immich-postgres", "immich-redis"],
        "health_check": "http://localhost:2283/api/server-info",
        "restart_order": ["postgres", "redis", "server"]
    },
    "myai": {
        "containers": ["myai-*"],  # Wildcard pattern
        "health_check": "container_status",
        "restart_order": "dependency_order"
    }
}
```

#### Problem Detection Pattern
```python
def detect_restart_loops(threshold_minutes: int = 10):
    """Austrian efficiency: Don't just detect, understand WHY."""
    containers = get_containers_with_restarts()
    
    for container in containers:
        if container["restart_count"] > 3:
            # Analyze logs for root cause
            logs = get_container_logs(container["name"], lines=50)
            error_patterns = analyze_error_patterns(logs)
            
            yield {
                "container": container["name"],
                "restart_count": container["restart_count"],
                "probable_cause": determine_root_cause(error_patterns),
                "suggested_fix": get_fix_recommendation(error_patterns)
            }
```

### 4. Code Generation Guidelines

#### When Windsurf generates Docker code:
1. Always include error handling with structured responses
2. Use Austrian efficiency comments: `# Sandra's insight: "explanation"`
3. Include timeout parameters for all Docker commands
4. Return JSON-compatible dictionaries
5. Add proper type hints

#### When Windsurf generates MCP tools:
1. Use `@app.tool()` decorator
2. Include comprehensive docstrings
3. Validate input parameters
4. Return standardized response format
5. Log operations for debugging

### 5. Testing Patterns

#### MCP Tool Testing
```python
def test_list_containers():
    """Test container listing with various scenarios."""
    # Test normal case
    result = list_containers()
    assert result["success"] is True
    assert "containers" in result
    
    # Test error case (Docker not available)
    with mock.patch('subprocess.run') as mock_run:
        mock_run.side_effect = FileNotFoundError("docker not found")
        result = list_containers()
        assert result["success"] is False
        assert "error" in result
```

### 6. Documentation Standards

#### Function Documentation
```python
def docker_operation(param: str) -> Dict[str, Any]:
    """
    One-line summary of what this does.
    
    Sandra's use case: Explain why this exists for her workflow.
    
    Args:
        param: Description with examples
        
    Returns:
        Dict with 'success' bool and 'data'/'error' fields
        
    Example:
        >>> result = docker_operation("test")
        >>> print(result["success"])
        True
    """
```

#### Austrian Efficiency Documentation
- Include "Sandra's insight:" comments for domain knowledge
- Document Vienna-specific patterns and reasoning
- Explain automation decisions and trade-offs
- Reference real stack examples (Veogen, Immich, MyAI)

### 7. Deployment Patterns

#### DXT Packaging
```json
{
  "name": "dockermcp",
  "version": "0.1.0",
  "description": "Austrian efficiency Docker operations for Claude Desktop",
  "mcpServers": {
    "dockermcp": {
      "command": "python",
      "args": ["-m", "dockermcp.server"],
      "env": {
        "DOCKER_HOST": "unix:///var/run/docker.sock"
      }
    }
  }
}
```

## Implementation Priorities

### Phase 1: Core Functionality (Days 1-2)
1. Fix import errors with stub modules
2. Add basic FastMCP tool decorators  
3. Test container operations
4. Create minimal DXT package

### Phase 2: Feature Completion (Days 3-5)
1. Implement missing Docker operations
2. Add proper error handling throughout
3. Create test suite
4. Document actual capabilities

### Phase 3: Austrian Efficiency (Days 6-10) 
1. Add Vienna stack intelligence
2. Implement problem detection
3. Create automation workflows
4. Performance optimization

---
*"In Vienna, even the containers run on time."* - Austrian efficiency applied to Docker operations
