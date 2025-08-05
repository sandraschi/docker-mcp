#!/usr/bin/env python3
"""
Sandra's Docker MCP Server - Austrian Efficiency Edition
Built with FastMCP 2.10 - Comprehensive Docker operations + Workflow intelligence

Features:
- 25 bread-and-butter Docker operations (complete CRUD)
- 15 Austrian efficiency workflow tools (stack health, problem detection)
- DIY customization framework for forkers
- Vienna-specific intelligence for Sandra's environment
"""

import asyncio
import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

import fastmcp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our specialized modules
from docker_ops.containers import ContainerManager
from docker_ops.images import ImageManager
from docker_ops.networks import NetworkManager
from docker_ops.volumes import VolumeManager
from docker_ops.system import SystemManager
from workflow_intel.stack_health import StackHealthChecker
from workflow_intel.problem_detection import ProblemDetector
from workflow_intel.automation import AutomationManager
from workflow_intel.vienna_specific import ViennaEnvironment

# Initialize FastMCP server
mcp = fastmcp.FastMCP("Sandra's Docker MCP Server")

# Initialize managers
container_mgr = ContainerManager()
image_mgr = ImageManager()
network_mgr = NetworkManager()
volume_mgr = VolumeManager()
system_mgr = SystemManager()
stack_health = StackHealthChecker()
problem_detector = ProblemDetector()
automation_mgr = AutomationManager()
vienna_env = ViennaEnvironment()

# ============================================================================
# PART 1: BREAD-AND-BUTTER DOCKER OPERATIONS
# Standard Docker CRUD operations - the foundation
# ============================================================================

# CONTAINER LIFECYCLE OPERATIONS
@mcp.tool()
def list_containers(all_states: bool = True) -> Dict[str, Any]:
    """
    List all Docker containers with status information.
    
    Args:
        all_states: Include stopped containers (default: True)
        
    Returns:
        Dictionary with container list and summary statistics
    """
    return container_mgr.list_containers(all_states)

@mcp.tool()
def get_container_info(container_name: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific container.
    
    Args:
        container_name: Name or ID of the container
        
    Returns:
        Detailed container information including status, ports, volumes
    """
    return container_mgr.get_container_info(container_name)

@mcp.tool()
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

@mcp.tool()
def start_container(container_name: str) -> Dict[str, Any]:
    """
    Start a stopped container.
    
    Args:
        container_name: Name or ID of the container
        
    Returns:
        Start operation result
    """
    return container_mgr.start_container(container_name)

@mcp.tool()
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

@mcp.tool()
def restart_container(container_name: str) -> Dict[str, Any]:
    """
    Restart a container (stop + start).
    
    Args:
        container_name: Name or ID of the container
        
    Returns:
        Restart operation result
    """
    return container_mgr.restart_container(container_name)

@mcp.tool()
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

@mcp.tool()
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

# IMAGE MANAGEMENT OPERATIONS
@mcp.tool()
def list_images(include_unused: bool = True) -> Dict[str, Any]:
    """
    List all Docker images with size and usage information.
    THE MISSING FUNCTION that broke our current tool!
    
    Args:
        include_unused: Include images not used by any container
        
    Returns:
        Image list with size, age, and usage status
    """
    return image_mgr.list_images(include_unused)

@mcp.tool()
def get_image_status(image_name: str) -> Dict[str, Any]:
    """
    Get detailed status of a specific image.
    Sandra's insight: "weed out the year old zombies"
    
    Args:
        image_name: Image name or ID
        
    Returns:
        Image details with age, size, usage, and cleanup recommendation
    """
    return image_mgr.get_image_status(image_name)

@mcp.tool()
def pull_image(image_name: str, tag: str = "latest") -> Dict[str, Any]:
    """
    Pull an image from Docker registry.
    
    Args:
        image_name: Image name (e.g., "nginx")
        tag: Image tag (default: "latest")
        
    Returns:
        Pull operation result with size and layers info
    """
    return image_mgr.pull_image(image_name, tag)

@mcp.tool()
def remove_image(image_name: str, force: bool = False) -> Dict[str, Any]:
    """
    Remove a Docker image.
    
    Args:
        image_name: Image name or ID
        force: Force removal even if used by containers
        
    Returns:
        Remove operation result
    """
    return image_mgr.remove_image(image_name, force)

@mcp.tool()
def tag_image(source_image: str, target_tag: str) -> Dict[str, Any]:
    """
    Tag an image with a new name/tag.
    
    Args:
        source_image: Source image name or ID
        target_tag: New tag (e.g., "myapp:v1.0")
        
    Returns:
        Tag operation result
    """
    return image_mgr.tag_image(source_image, target_tag)

# NETWORK OPERATIONS
@mcp.tool()
def list_networks() -> Dict[str, Any]:
    """
    List Docker networks with connection information.
    
    Returns:
        Network list with connected containers
    """
    return network_mgr.list_networks()

@mcp.tool()
def create_network(name: str, driver: str = "bridge") -> Dict[str, Any]:
    """
    Create a new Docker network.
    
    Args:
        name: Network name
        driver: Network driver (bridge, host, overlay)
        
    Returns:
        Network creation result
    """
    return network_mgr.create_network(name, driver)

@mcp.tool()
def remove_network(name: str) -> Dict[str, Any]:
    """
    Remove a Docker network.
    
    Args:
        name: Network name or ID
        
    Returns:
        Remove operation result
    """
    return network_mgr.remove_network(name)

# VOLUME OPERATIONS
@mcp.tool()
def list_volumes() -> Dict[str, Any]:
    """
    List Docker volumes with usage information.
    
    Returns:
        Volume list with size and mount information
    """
    return volume_mgr.list_volumes()

@mcp.tool()
def create_volume(name: str) -> Dict[str, Any]:
    """
    Create a new Docker volume.
    
    Args:
        name: Volume name
        
    Returns:
        Volume creation result
    """
    return volume_mgr.create_volume(name)

@mcp.tool()
def remove_volume(name: str, force: bool = False) -> Dict[str, Any]:
    """
    Remove a Docker volume.
    
    Args:
        name: Volume name
        force: Force removal even if in use
        
    Returns:
        Remove operation result
    """
    return volume_mgr.remove_volume(name, force)

# SYSTEM OPERATIONS
@mcp.tool()
def docker_system_info() -> Dict[str, Any]:
    """
    Get Docker system information and status.
    
    Returns:
        System information including version, storage, and resource usage
    """
    return system_mgr.get_system_info()

@mcp.tool()
def docker_version() -> Dict[str, Any]:
    """
    Get Docker version information.
    
    Returns:
        Docker version details for client and server
    """
    return system_mgr.get_version()

@mcp.tool()
def docker_disk_usage() -> Dict[str, Any]:
    """
    Get Docker disk usage breakdown.
    
    Returns:
        Disk usage by images, containers, volumes, and cache
    """
    return system_mgr.get_disk_usage()

@mcp.tool()
def docker_system_prune(
    volumes: bool = False,
    networks: bool = False,
    force: bool = False
) -> Dict[str, Any]:
    """
    Clean up unused Docker resources.
    
    Args:
        volumes: Also remove unused volumes
        networks: Also remove unused networks  
        force: Don't prompt for confirmation
        
    Returns:
        Cleanup operation result with space reclaimed
    """
    return system_mgr.system_prune(volumes, networks, force)

# ============================================================================
# PART 2: AUSTRIAN EFFICIENCY WORKFLOW INTELLIGENCE
# Sandra's environment-specific smart tools
# ============================================================================

# STACK HEALTH INTELLIGENCE
@mcp.tool()
def vienna_dev_status() -> Dict[str, Any]:
    """
    Sandra's complete dev environment status - Austrian efficiency style.
    One call for complete situational awareness of all stacks.
    
    Returns:
        Complete environment health with Gemütlichkeit factor
    """
    return vienna_env.get_dev_status()

@mcp.tool()
def check_veogen_stack() -> Dict[str, Any]:
    """
    Complete Veogen stack health check.
    Components: backend + redis + postgres + grafana + node-exporter
    
    Returns:
        Veogen stack health with dependency analysis
    """
    return stack_health.check_veogen_stack()

@mcp.tool()
def check_myai_health() -> Dict[str, Any]:
    """
    Health check for all MyAI projects portfolio.
    Known projects: document-viewer, calibre-plus, bob-and-alice, etc.
    
    Returns:
        MyAI projects health summary with restart loop detection
    """
    return stack_health.check_myai_health()

@mcp.tool()
def check_immich_stack() -> Dict[str, Any]:
    """
    Immich photo management stack health.
    Components: server + postgres + redis + machine_learning
    
    Returns:
        Immich stack health with performance metrics
    """
    return stack_health.check_immich_stack()

# PROBLEM DETECTION & DIAGNOSIS
@mcp.tool()
def find_restart_loops(threshold_minutes: int = 10) -> Dict[str, Any]:
    """
    Find containers stuck in restart loops with root cause analysis.
    Austrian efficiency: Don't just detect, understand WHY.
    
    Args:
        threshold_minutes: Time window for restart detection
        
    Returns:
        Restart loop analysis with suggested fixes
    """
    return problem_detector.find_restart_loops(threshold_minutes)

@mcp.tool()
def check_frontend_health() -> Dict[str, Any]:
    """
    Sandra's insight: "frontends with no exposed ports" = broken.
    Find web frontends that should have ports but don't.
    
    Returns:
        Frontend health analysis with connectivity tests
    """
    return problem_detector.check_frontend_health()

@mcp.tool()
def detect_dependency_issues() -> Dict[str, Any]:
    """
    Detect containers waiting for dependencies (databases, Redis, etc.)
    Focus on actual blocking relationships in Sandra's stacks.
    
    Returns:
        Dependency issue analysis with startup order recommendations
    """
    return problem_detector.detect_dependency_issues()

@mcp.tool()
def find_missing_containers() -> Dict[str, Any]:
    """
    Detect expected containers that don't exist (like zen_goldstine).
    Knows Sandra's expected container ecosystem.
    
    Returns:
        Missing container report with recreation instructions
    """
    return problem_detector.find_missing_containers()

# INTELLIGENT AUTOMATION
@mcp.tool()
def fix_restart_loops(container_name: str, strategy: str = "smart") -> Dict[str, Any]:
    """
    Actually fix restart loops, don't just report them.
    Strategies: restart_fresh, update_image, fix_dependencies, resource_adjust
    
    Args:
        container_name: Container with restart loop
        strategy: Fix strategy (smart, restart_fresh, update_image, fix_dependencies)
        
    Returns:
        Fix operation result with success/failure details
    """
    return automation_mgr.fix_restart_loops(container_name, strategy)

@mcp.tool()
def smart_stack_restart(stack_name: str) -> Dict[str, Any]:
    """
    Restart stacks in proper dependency order.
    Knows: Veogen, Immich, MyAI dependency chains
    
    Args:
        stack_name: Stack to restart (veogen, immich, myai)
        
    Returns:
        Stack restart result with dependency coordination
    """
    return automation_mgr.smart_stack_restart(stack_name)

@mcp.tool()
def emergency_stack_recovery(stack_name: str) -> Dict[str, Any]:
    """
    Nuclear option: Complete stack recovery when everything is broken.
    One command for catastrophic failure recovery.
    
    Args:
        stack_name: Stack to recover (veogen, immich, myai)
        
    Returns:
        Emergency recovery result with rollback capability
    """
    return automation_mgr.emergency_stack_recovery(stack_name)

# SPECIALIZED RECOVERY
@mcp.tool()
def zen_goldstine_recovery() -> Dict[str, Any]:
    """
    Specialized recovery for missing zen_goldstine (fetch MCP).
    Knows exactly how to recreate this critical container.
    
    Returns:
        zen_goldstine recovery result with MCP integration status
    """
    return vienna_env.zen_goldstine_recovery()

@mcp.tool()
def find_zombie_images(age_threshold_days: int = 90) -> Dict[str, Any]:
    """
    Find old, unused images eating disk space.
    Sandra's insight: "weed out the year old zombies"
    
    Args:
        age_threshold_days: Age threshold for zombie detection
        
    Returns:
        Zombie image report with cleanup recommendations
    """
    return problem_detector.find_zombie_images(age_threshold_days)

@mcp.tool()
def maintenance_recommendations() -> Dict[str, Any]:
    """
    Proactive maintenance suggestions. Austrian efficiency.
    Prevent problems before they happen.
    
    Returns:
        Maintenance recommendations with priority levels
    """
    return vienna_env.maintenance_recommendations()

# ============================================================================
# SERVER STARTUP AND CONFIGURATION
# ============================================================================

def main():
    """
    Start Sandra's Docker MCP Server with Austrian efficiency.
    """
    logger.info("🚀 Starting Sandra's Docker MCP Server - Austrian Efficiency Edition")
    logger.info("📊 Features: 25 Docker CRUD + 15 Workflow Intelligence Tools")
    logger.info("🏛️ Vienna-specific environment optimization enabled")
    
    # Verify Docker is available
    try:
        result = subprocess.run(['docker', 'version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            logger.error("❌ Docker not available or not running")
            sys.exit(1)
        logger.info("✅ Docker connection verified")
    except Exception as e:
        logger.error(f"❌ Docker verification failed: {e}")
        sys.exit(1)
    
    # Start the FastMCP server
    logger.info("🎯 Austrian efficiency: All systems operational")
    mcp.run()

if __name__ == "__main__":
    main()
