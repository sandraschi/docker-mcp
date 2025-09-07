"""
Stateful example tools for DockerMCP.

This module demonstrates the stateful capabilities of FastMCP 2.12
with Docker management use cases.
"""
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

# Import FastMCP components
from fastmcp.tools import Tool, get_tools_metadata
from fastmcp.exceptions import ToolError

# Configure logging
from dockermcp.logging_config import logger, configure_logging
configure_logging()

# Import the state manager
from dockermcp.state import get_state_manager

# Initialize state manager
state_manager = get_state_manager()

class ContainerStats(BaseModel):
    """Model for container statistics."""
    container_id: str
    name: str
    cpu_usage: float
    memory_usage: float
    network_io: Dict[str, int]
    timestamp: str

class TrackedContainers(BaseModel):
    """Model for tracking container statistics over time."""
    container_id: str
    name: str
    stats_history: List[ContainerStats] = Field(default_factory=list)

@Tool.register(
    name="track_container",
    description="Start tracking a container's statistics over time"
)
async def track_container(container_id: str, name: str) -> Dict[str, Any]:
    """
    Start tracking a container's statistics over time.
    
    Args:
        container_id: The ID of the container to track
        name: A friendly name for the container
        
    Returns:
        Confirmation of tracking status
    """
    try:
        # Create or update the tracked container
        tracked = await state_manager.get_state(f"tracked:{container_id}", TrackedContainers)
        if not tracked:
            tracked = TrackedContainers(container_id=container_id, name=name)
        
        # Store the updated tracking info
        await state_manager.set_state(f"tracked:{container_id}", tracked)
        
        return {
            "success": True,
            "message": f"Started tracking container {name} ({container_id})",
            "container_id": container_id
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to start tracking container: {str(e)}",
            "error": str(e)
        }

@Tool.register(
    name="update_container_stats",
    description="Update container statistics in the tracking system"
)
async def update_container_stats(
    container_id: str,
    cpu_usage: float,
    memory_usage: float,
    network_io: Dict[str, int],
    timestamp: str
) -> Dict[str, Any]:
    """
    Update container statistics in the tracking system.
    
    Args:
        container_id: The ID of the container
        cpu_usage: Current CPU usage percentage
        memory_usage: Current memory usage in MB
        network_io: Network I/O statistics
        timestamp: ISO format timestamp
        
    Returns:
        Status of the update operation
    """
    try:
        # Get the tracked container
        tracked = await state_manager.get_state(f"tracked:{container_id}", TrackedContainers)
        if not tracked:
            return {
                "success": False,
                "message": f"Container {container_id} is not being tracked",
                "error": "Container not tracked"
            }
        
        # Add new stats
        stats = ContainerStats(
            container_id=container_id,
            name=tracked.name,
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            network_io=network_io,
            timestamp=timestamp
        )
        
        # Keep only the last 100 data points
        tracked.stats_history.append(stats)
        if len(tracked.stats_history) > 100:
            tracked.stats_history = tracked.stats_history[-100:]
        
        # Update the state
        await state_manager.set_state(f"tracked:{container_id}", tracked)
        
        return {
            "success": True,
            "message": f"Updated stats for container {tracked.name}",
            "stats_count": len(tracked.stats_history)
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to update container stats: {str(e)}",
            "error": str(e)
        }

@Tool.register(
    name="get_container_history",
    description="Get historical statistics for a tracked container"
)
async def get_container_history(container_id: str) -> Dict[str, Any]:
    """
    Get historical statistics for a tracked container.
    
    Args:
        container_id: The ID of the container
        
    Returns:
        Container statistics history
    """
    try:
        tracked = await state_manager.get_state(f"tracked:{container_id}", TrackedContainers)
        if not tracked:
            return {
                "success": False,
                "message": f"Container {container_id} is not being tracked",
                "error": "Container not tracked"
            }
        
        return {
            "success": True,
            "container_id": container_id,
            "name": tracked.name,
            "stats_history": [stat.model_dump() for stat in tracked.stats_history]
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to get container history: {str(e)}",
            "error": str(e)
        }

# Export the tools for registration
def get_tools():
    """Return all tools in this module for registration."""
    return [
        track_container,
        update_container_stats,
        get_container_history
    ]
