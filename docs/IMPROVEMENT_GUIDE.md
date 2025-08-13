# DockerMCP Windsurf Improvement Guide (Continued)

## Specific Implementation Steps (Continued)

### 1. Fix ImportError Script (Continued)

```powershell
# Continue fix_imports.ps1 script

@"
class ProblemDetector:
    def __init__(self):
        pass
    
    def find_restart_loops(self, threshold_minutes: int = 10):
        return {"success": False, "error": "Not implemented yet"}
    
    def check_frontend_health(self):
        return {"success": False, "error": "Not implemented yet"}
    
    def detect_dependency_issues(self):
        return {"success": False, "error": "Not implemented yet"}
    
    def find_missing_containers(self):
        return {"success": False, "error": "Not implemented yet"}
    
    def find_zombie_images(self, age_threshold_days: int = 90):
        return {"success": False, "error": "Not implemented yet"}
"@ | Out-File -FilePath "src\workflow_intel\problem_detection.py" -Encoding UTF8

@"
class AutomationManager:
    def __init__(self):
        pass
    
    def fix_restart_loops(self, container_name: str, strategy: str = "smart"):
        return {"success": False, "error": "Not implemented yet"}
    
    def smart_stack_restart(self, stack_name: str):
        return {"success": False, "error": "Not implemented yet"}
    
    def emergency_stack_recovery(self, stack_name: str):
        return {"success": False, "error": "Not implemented yet"}
"@ | Out-File -FilePath "src\workflow_intel\automation.py" -Encoding UTF8

@"
class ViennaEnvironment:
    def __init__(self):
        pass
    
    def get_dev_status(self):
        return {"success": False, "error": "Not implemented yet"}
    
    def zen_goldstine_recovery(self):
        return {"success": False, "error": "Not implemented yet"}
    
    def maintenance_recommendations(self):
        return {"success": False, "error": "Not implemented yet"}
"@ | Out-File -FilePath "src\workflow_intel\vienna_specific.py" -Encoding UTF8

# Add __init__.py files
"" | Out-File -FilePath "src\docker_ops\__init__.py" -Encoding UTF8
"" | Out-File -FilePath "src\workflow_intel\__init__.py" -Encoding UTF8

Write-Host "✅ All missing modules created with stubs"
Write-Host "🚀 Test the server now: python -m src.server"
```

### 2. FastMCP 2.10 Integration Fix

**Current Problem**: No actual FastMCP usage  
**Solution**: Replace the main server structure

```python
# Create new file: src/fastmcp_server.py
#!/usr/bin/env python3
"""
Sandra's Docker MCP Server - FastMCP 2.10 Implementation
Proper FastMCP integration replacing subprocess-based approach
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from fastmcp import FastMCP

# Import our managers
from docker_ops.containers import ContainerManager
from docker_ops.images import ImageManager
from docker_ops.networks import NetworkManager
from docker_ops.volumes import VolumeManager
from docker_ops.system import SystemManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
app = FastMCP("Sandra's Docker MCP Server")

# Initialize managers
container_mgr = ContainerManager()
image_mgr = ImageManager()
network_mgr = NetworkManager()
volume_mgr = VolumeManager()
system_mgr = SystemManager()

# ============================================================================
# CONTAINER OPERATIONS
# ============================================================================

@app.tool()
def list_containers(all_states: bool = True) -> Dict[str, Any]:
    """
    List all Docker containers with status information.
    
    Args:
        all_states: Include stopped containers (default: True)
        
    Returns:
        Dictionary with container list and summary statistics
    """
    return container_mgr.list_containers(all_states)

@app.tool()
def get_container_info(container_name: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific container.
    
    Args:
        container_name: Name or ID of the container
        
    Returns:
        Detailed container information including status, ports, volumes
    """
    return container_mgr.get_container_info(container_name)

@app.tool()
def create_container(
    image: str,
    name: str,
    ports: Optional[Dict[str, str]] = None,
    environment: Optional[Dict[str, str]] = None,
    volumes: Optional[Dict[str, str]] = None,
    network: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new Docker container from an image.
    
    Args:
        image: Docker image name (e.g., "nginx:latest")
        name: Container name
        ports: Port mappings {"container_port": "host_port"}
        environment: Environment variables {"KEY": "value"}
        volumes: Volume mounts {"host_path": "container_path"}
        network: Network to connect to
        
    Returns:
        Container creation result with ID and status
    """
    return container_mgr.create_container(image, name, ports, environment, volumes, network)

@app.tool()
def start_container(container_name: str) -> Dict[str, Any]:
    """
    Start a stopped container.
    
    Args:
        container_name: Name or ID of the container
        
    Returns:
        Start operation result
    """
    return container_mgr.start_container(container_name)

@app.tool()
def stop_container(container_name: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Stop a running container gracefully.
    
    Args:
        container_name: Name or ID of the container
        timeout: Seconds to wait before force killing
        
    Returns:
        Stop operation result
    """
    return container_mgr.stop_container(container_name, timeout)

@app.tool()
def restart_container(container_name: str) -> Dict[str, Any]:
    """
    Restart a container (stop + start).
    
    Args:
        container_name: Name or ID of the container
        
    Returns:
        Restart operation result
    """
    return container_mgr.restart_container(container_name)

@app.tool()
def remove_container(container_name: str, force: bool = False) -> Dict[str, Any]:
    """
    Remove a container.
    
    Args:
        container_name: Name or ID of the container
        force: Force removal of running container
        
    Returns:
        Remove operation result
    """
    return container_mgr.remove_container(container_name, force)

@app.tool()
def get_container_logs(
    container_name: str,
    lines: int = 100,
    follow: bool = False,
    timestamps: bool = True
) -> Dict[str, Any]:
    """
    Get container logs with formatting and error highlighting.
    
    Args:
        container_name: Name or ID of the container
        lines: Number of recent lines to retrieve
        follow: Stream logs (not recommended for MCP)
        timestamps: Include timestamps in output
        
    Returns:
        Container logs with metadata
    """
    return container_mgr.get_container_logs(container_name, lines, follow, timestamps)

# ============================================================================
# SYSTEM OPERATIONS (Basic implementations)
# ============================================================================

@app.tool()
def docker_system_info() -> Dict[str, Any]:
    """
    Get Docker system information and status.
    
    Returns:
        System information including version, storage, and resource usage
    """
    try:
        # For now, delegate to system manager (which will be implemented)
        return system_mgr.get_system_info()
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.tool()
def docker_version() -> Dict[str, Any]:
    """
    Get Docker version information.
    
    Returns:
        Docker version details for client and server
    """
    try:
        return system_mgr.get_version()
    except Exception as e:
        return {"success": False, "error": str(e)}

# ============================================================================
# SERVER STARTUP
# ============================================================================

def main():
    """
    Start Sandra's Docker MCP Server with Austrian efficiency.
    """
    logger.info("🚀 Starting Sandra's Docker MCP Server - FastMCP 2.10 Edition")
    logger.info("🐳 Docker MCP tools loaded and ready")
    logger.info("🎯 Austrian efficiency: All systems operational")
    
    # Start the FastMCP server
    app.run()

if __name__ == "__main__":
    main()
```

### 3. Update DXT Manifest

```json
{
  "name": "dockermcp",
  "version": "0.1.0",
  "description": "FastMCP 2.10 server for Docker operations with Austrian efficiency",
  "author": "Sandra Schimanovich",
  "homepage": "https://github.com/sandraschi/dockermcp",
  "mcpServers": {
    "dockermcp": {
      "command": "python",
      "args": ["-m", "dockermcp.fastmcp_server"],
      "env": {
        "DOCKER_HOST": "unix:///var/run/docker.sock"
      }
    }
  },
  "dependencies": {
    "fastmcp": ">=2.10.0",
    "docker": ">=6.0.0",
    "pydantic": ">=1.10.0"
  }
}
```

## Advanced Windsurf Optimization

### 1. Create Project-Specific Prompts

```markdown
# .windsurf/prompts/docker_operations.md

## Docker Command Generation

When generating Docker operations:

1. **Always use the ContainerManager pattern**:
```python
def new_docker_operation(self, param: str) -> Dict[str, Any]:
    result = self._run_docker_command(["docker", "subcommand", param])
    if result["success"]:
        return {"success": True, "data": result["stdout"]}
    else:
        return {"success": False, "error": result["stderr"]}
```

2. **Austrian Efficiency Comments**:
- Add insights like: `# Sandra's insight: "Veogen needs this for stack health"`
- Document Vienna-specific reasoning
- Explain automation trade-offs

3. **Error Handling Pattern**:
```python
try:
    # Docker operation
    return {"success": True, "data": result}
except subprocess.TimeoutExpired:
    return {"success": False, "error": "Operation timed out"}
except Exception as e:
    return {"success": False, "error": str(e)}
```

## Vienna Stack Knowledge

### Veogen Stack
- **Containers**: veogen-backend, veogen-redis, veogen-postgres
- **Health Check**: `http://localhost:8000/health`
- **Common Issues**: Redis connection failures, DB migrations
- **Restart Order**: postgres → redis → backend

### Immich Stack  
- **Containers**: immich-server, immich-postgres, immich-redis, immich-machine-learning
- **Health Check**: `http://localhost:2283/api/server-info`
- **Common Issues**: ML container memory issues, photo indexing
- **Restart Order**: postgres → redis → server → machine-learning

### MyAI Projects
- **Pattern**: myai-* containers (multiple projects)
- **Health Check**: Container status + port checks
- **Common Issues**: Port conflicts, dependency chains
- **Strategy**: Individual project health checks
```

### 2. Optimize Windsurf Rules Priority

**Current**: 32KB generic rules  
**Target**: 5KB focused rules

```markdown
# .windsurf/rules/dockermcp_priority.md

## Rule Priority for DockerMCP

### HIGHEST PRIORITY
1. FastMCP 2.10 tool patterns
2. Docker subprocess error handling  
3. Austrian efficiency workflow patterns
4. Sandra's Vienna stack knowledge

### MEDIUM PRIORITY
1. Python typing and error handling
2. Testing patterns for MCP tools
3. DXT packaging requirements

### LOWEST PRIORITY
1. Generic software development rules
2. Non-Docker infrastructure patterns
3. Abstract architectural guidance
```

### 3. Code Generation Templates

```markdown
# .windsurf/templates/fastmcp_tool.py

@app.tool()
def {operation_name}({parameters}) -> Dict[str, Any]:
    """
    {description}
    
    Sandra's use case: {vienna_context}
    
    Args:
        {parameter_docs}
        
    Returns:
        Structured result with success/error handling
    """
    try:
        # {implementation_notes}
        result = {manager_name}.{operation_method}({params})
        
        if result["success"]:
            return {
                "success": True,
                "data": result["data"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            return {
                "success": False,
                "error": result["error"]
            }
            
    except Exception as e:
        logger.error(f"Error in {operation_name}: {str(e)}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }
```

## Testing Strategy Implementation

### 1. Create Test Framework

```python
# tests/test_container_operations.py
import pytest
import json
from unittest.mock import patch, MagicMock
from docker_ops.containers import ContainerManager

class TestContainerManager:
    
    def setup_method(self):
        self.container_mgr = ContainerManager()
    
    @patch('subprocess.run')
    def test_list_containers_success(self, mock_run):
        """Test successful container listing."""
        # Mock successful docker ps output
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"ID":"abc123","Names":"test","Status":"Up 5 minutes"}'
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        result = self.container_mgr.list_containers()
        
        assert result["success"] is True
        assert len(result["containers"]) == 1
        assert result["containers"][0]["name"] == "test"
    
    @patch('subprocess.run')
    def test_list_containers_docker_not_running(self, mock_run):
        """Test container listing when Docker is not running."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Cannot connect to the Docker daemon"
        mock_run.return_value = mock_result
        
        result = self.container_mgr.list_containers()
        
        assert result["success"] is False
        assert "Cannot connect" in result["error"]
    
    def test_container_manager_initialization(self):
        """Test ContainerManager initializes correctly."""
        assert self.container_mgr.docker_cmd == ["docker"]
```

### 2. Create Performance Tests

```python
# tests/test_performance.py
import time
import pytest
from docker_ops.containers import ContainerManager

class TestPerformance:
    
    @pytest.mark.performance
    def test_list_containers_performance(self):
        """Test that container listing completes within reasonable time."""
        container_mgr = ContainerManager()
        
        start_time = time.time()
        result = container_mgr.list_containers()
        end_time = time.time()
        
        # Should complete within 5 seconds
        assert (end_time - start_time) < 5.0
        
        # Should return structured result
        assert "success" in result
        assert "containers" in result or "error" in result
```

## Deployment and Monitoring

### 1. Health Check Implementation

```python
# Add to fastmcp_server.py

@app.tool()
def health_check() -> Dict[str, Any]:
    """
    Comprehensive health check for Docker MCP server.
    
    Returns:
        Health status including Docker connectivity and system resources
    """
    health_status = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "server": "healthy",
        "docker": "unknown",
        "features": {
            "containers": False,
            "images": False,
            "networks": False,
            "volumes": False
        }
    }
    
    try:
        # Test Docker connectivity
        result = container_mgr._run_docker_command(["version"], timeout=5)
        if result["success"]:
            health_status["docker"] = "healthy"
            health_status["features"]["containers"] = True
        else:
            health_status["docker"] = "unhealthy"
            health_status["error"] = result.get("error", "Docker not responding")
            
    except Exception as e:
        health_status["docker"] = "error"
        health_status["error"] = str(e)
    
    return health_status
```

### 2. Monitoring Integration

```python
# monitoring/docker_metrics.py
import time
import json
from typing import Dict, Any
from docker_ops.containers import ContainerManager

class DockerMetrics:
    """Collect Docker metrics for monitoring."""
    
    def __init__(self):
        self.container_mgr = ContainerManager()
    
    def collect_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive Docker metrics."""
        metrics = {
            "timestamp": time.time(),
            "containers": self._get_container_metrics(),
            "system": self._get_system_metrics()
        }
        return metrics
    
    def _get_container_metrics(self) -> Dict[str, Any]:
        """Get container-specific metrics."""
        result = self.container_mgr.list_containers()
        
        if not result["success"]:
            return {"error": result["error"]}
        
        summary = result.get("summary", {})
        return {
            "total": summary.get("total", 0),
            "running": summary.get("running", 0),
            "stopped": summary.get("stopped", 0),
            "error": summary.get("error", 0)
        }
    
    def _get_system_metrics(self) -> Dict[str, Any]:
        """Get system-level Docker metrics."""
        # This would integrate with system manager
        return {"status": "not_implemented"}
```

## Final Integration Checklist

### Phase 1: Emergency Fix (Day 1)
- [ ] Run `fix_imports.ps1` script
- [ ] Test server startup: `python -m src.server`
- [ ] Verify basic container operations work
- [ ] Create emergency DXT package

### Phase 2: FastMCP Integration (Day 2)
- [ ] Replace server.py with fastmcp_server.py
- [ ] Test FastMCP tool decorators
- [ ] Verify MCP protocol compliance
- [ ] Update DXT manifest

### Phase 3: Windsurf Optimization (Day 3)
- [ ] Replace generic rules with dockermcp_rules.md
- [ ] Create project-specific prompts
- [ ] Test Windsurf code generation improvements
- [ ] Document Austrian efficiency patterns

### Phase 4: Testing and Polish (Days 4-5)
- [ ] Implement test framework
- [ ] Add performance monitoring
- [ ] Create health check endpoints
- [ ] Complete documentation review

## Success Metrics

### Technical Metrics
- **Server Startup**: Must complete without ImportError
- **Tool Coverage**: 8 working tools minimum (current container operations)
- **Error Rate**: <5% for basic Docker operations
- **Response Time**: <2 seconds for container listing

### Windsurf Efficiency Metrics
- **Rule Size**: Reduce from 32KB to <5KB focused rules
- **Code Generation**: Improve Docker pattern recognition
- **Austrian Context**: Include Vienna-specific stack knowledge
- **Development Speed**: 50% faster common Docker operations

### User Experience Metrics
- **Documentation Accuracy**: Match claimed vs actual features
- **Error Messages**: Clear, actionable error descriptions
- **Workflow Integration**: Seamless Claude Desktop DXT installation
- **Maintenance**: Automated health checks and problem detection

---

**Implementation Note**: Start with the emergency fixes to make the repository functional, then systematically implement the Austrian efficiency features that make this unique among Docker MCP servers.

*"Austrian efficiency means building what works, documenting what exists, and optimizing what matters."* - Sandra's development philosophy
