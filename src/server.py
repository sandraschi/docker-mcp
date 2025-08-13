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
vienna_env = ViennaEnvironment()

# ============================================================================
# PART 1: BREAD-AND-BUTTER DOCKER OPERATIONS
# Standard Docker CRUD operations - the foundation
# ============================================================================

# CONTAINER LIFECYCLE OPERATIONS
@mcp.tool()
@mcp.tool()
async def list_containers(all_states: bool = True) -> Dict[str, Any]:
    """
    List all Docker containers with status information.
    
    Args:
        all_states: Include stopped containers (default: True)
        
    Returns:
        Dictionary with container list and summary statistics
    """
    try:
        # Use the container manager to list containers
        result = container_mgr.list_containers(all_states=all_states)
        return {
            'success': True,
            'containers': result.get('containers', []),
            'total': result.get('total', 0),
            'running': result.get('running', 0),
            'stopped': result.get('stopped', 0)
        }
    except Exception as e:
        logger.error(f"Error listing containers: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to list containers: {str(e)}",
            'containers': [],
            'total': 0,
            'running': 0,
            'stopped': 0
        }

@mcp.tool()
async def get_container_info(container_name: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific container.
    
    Args:
        container_name: Name or ID of the container
        
    Returns:
        Container details including configuration and state
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: container_mgr.get_container_info(container_name)
        )
    except Exception as e:
        logger.error(f"Error getting container info for {container_name}: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to get container info: {str(e)}",
            'container_id': container_name
        }

@mcp.tool()
@mcp.tool()
async def create_container(
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
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: container_mgr.create_container(
                image=image,
                name=name,
                ports=ports or {},
                environment=environment or {},
                volumes=volumes or {},
                network=network
            )
        )
    except Exception as e:
        logger.error(f"Error creating container {name} from image {image}: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to create container {name}: {str(e)}",
            'container_id': name
        }

@mcp.tool()
@mcp.tool()
async def start_container(container_name: str) -> Dict[str, Any]:
    """
    Start a stopped container.
    
    Args:
        container_name: Name or ID of the container
        
    Returns:
        Start operation result with status and container info
    """
    try:
        result = await container_mgr.start_container(container_name)
        return {
            'success': True,
            'container': result
        }
    except Exception as e:
        logger.error(f"Error starting container {container_name}: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to start container: {str(e)}",
            'container_id': container_name
        }

@mcp.tool()
@mcp.tool()
async def stop_container(container_name: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Stop a running container gracefully.
    
    Args:
        container_name: Name or ID of the container
        timeout: Seconds to wait before force killing
        
    Returns:
        Stop operation result with status and container info
    """
    try:
        result = await container_mgr.stop_container(container_name, timeout)
        return {
            'success': True,
            'container': result
        }
    except Exception as e:
        logger.error(f"Error stopping container {container_name}: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to stop container: {str(e)}",
            'container_id': container_name
        }

@mcp.tool()
@mcp.tool()
async def restart_container(container_name: str) -> Dict[str, Any]:
    """
    Restart a container (stop + start).
    
    Args:
        container_name: Name or ID of the container
        
    Returns:
        Restart operation result with status and container info
    """
    try:
        # First stop the container
        stop_result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: container_mgr.stop_container(container_name)
        )
        
        if not stop_result.get('success', False):
            return stop_result
            
        # Then start it again
        start_result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: container_mgr.start_container(container_name)
        )
        
        return {
            'success': start_result.get('success', False),
            'container': container_name,
            'status': 'restarted' if start_result.get('success') else 'failed_to_start',
            'details': {
                'stop_result': stop_result,
                'start_result': start_result
            }
        }
    except Exception as e:
        logger.error(f"Error restarting container {container_name}: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to restart container: {str(e)}",
            'container': container_name
        }

@mcp.tool()
@mcp.tool()
async def remove_container(container_name: str, force: bool = False) -> Dict[str, Any]:
    """
    Remove a container.
    
    Args:
        container_name: Name or ID of the container
        force: Force removal of running container
        
    Returns:
        Remove operation result with status and container info
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: container_mgr.remove_container(container_name, force)
        )
    except Exception as e:
        logger.error(f"Error removing container {container_name}: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to remove container: {str(e)}",
            'container_id': container_name
        }

@mcp.tool()
@mcp.tool()
async def get_container_logs(
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
        Dictionary containing logs and metadata
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: container_mgr.get_logs(container_name, lines, follow, timestamps)
        )
    except Exception as e:
        logger.error(f"Error getting logs for container {container_name}: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to get logs for container {container_name}: {str(e)}",
            'container': container_name,
            'logs': ''
        }

# IMAGE MANAGEMENT OPERATIONS
@mcp.tool()
async def list_images(include_unused: bool = True) -> Dict[str, Any]:
    """
    List all Docker images with size and usage information.
    
    Args:
        include_unused: Include images not used by any container
        
    Returns:
        Dictionary containing image list with size, age, and usage status
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: image_mgr.list_images(include_unused)
        )
    except Exception as e:
        logger.error(f"Error listing images: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to list images: {str(e)}",
            'images': []
        }

@mcp.tool()
async def get_image_status(image_name: str) -> Dict[str, Any]:
    """
    Get detailed status of a specific image.
    
    Args:
        image_name: Image name or ID
        
    Returns:
        Dictionary containing image details with age, size, usage, and cleanup recommendation
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: image_mgr.get_image_status(image_name)
        )
    except Exception as e:
        logger.error(f"Error getting status for image {image_name}: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to get status for image {image_name}: {str(e)}",
            'image': image_name
        }

@mcp.tool()
async def pull_image(image_name: str, tag: str = "latest") -> Dict[str, Any]:
    """
    Pull a Docker image from a registry.
    
    Args:
        image_name: Name of the image to pull
        tag: Image tag/version (default: latest)
        
    Returns:
        Dictionary containing pull operation result with status and image info
    """
    full_image_name = f"{image_name}:{tag}"
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: image_mgr.pull_image(full_image_name)
        )
    except Exception as e:
        logger.error(f"Error pulling image {full_image_name}: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to pull image {full_image_name}: {str(e)}",
            'image': full_image_name
        }

@mcp.tool()
async def remove_image(image_name: str, force: bool = False) -> Dict[str, Any]:
    """
    Remove a Docker image.
    
    Args:
        image_name: Name or ID of the image to remove
        force: Force removal of the image
        
    Returns:
        Dictionary containing remove operation result with status and freed space
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: image_mgr.remove_image(image_name, force)
        )
    except Exception as e:
        logger.error(f"Error removing image {image_name}: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to remove image {image_name}: {str(e)}",
            'image': image_name
        }

@mcp.tool()
async def tag_image(source_image: str, target_tag: str) -> Dict[str, Any]:
    """
    Tag a Docker image with a new tag.
    
    Args:
        source_image: Source image name or ID
        target_tag: New tag to apply (format: repo:tag)
        
    Returns:
        Dictionary containing tag operation result with status and image info
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: image_mgr.tag_image(source_image, target_tag)
        )
    except Exception as e:
        logger.error(f"Error tagging image {source_image} as {target_tag}: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to tag image {source_image} as {target_tag}: {str(e)}",
            'source_image': source_image,
            'target_tag': target_tag
        }

# NETWORK OPERATIONS
@mcp.tool()
async def list_networks() -> Dict[str, Any]:
    """
    List all Docker networks with driver and container info.
    
    Returns:
        Dictionary containing list of networks with their configurations
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: network_mgr.list_networks()
        )
    except Exception as e:
        logger.error(f"Error listing networks: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to list networks: {str(e)}",
            'networks': []
        }

@mcp.tool()
async def create_network(name: str, driver: str = "bridge") -> Dict[str, Any]:
    """
    Create a new Docker network.
    
    Args:
        name: Network name
        driver: Network driver (bridge, overlay, etc.)
        
    Returns:
        Dictionary containing network creation result with ID and details
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: network_mgr.create_network(name, driver)
        )
    except Exception as e:
        logger.error(f"Error creating network {name} with driver {driver}: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to create network {name}: {str(e)}",
            'network': name,
            'driver': driver
        }

@mcp.tool()
async def remove_network(name: str) -> Dict[str, Any]:
    """
    Remove a Docker network.
    
    Args:
        name: Network name or ID
        
    Returns:
        Dictionary containing remove operation result with status
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: network_mgr.remove_network(name)
        )
    except Exception as e:
        logger.error(f"Error removing network {name}: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to remove network {name}: {str(e)}",
            'network': name
        }

# VOLUME OPERATIONS
@mcp.tool()
async def list_volumes() -> Dict[str, Any]:
    """
    List all Docker volumes with usage information.
    
    Returns:
        Dictionary containing list of volumes with size and mount points
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            volume_mgr.list_volumes
        )
    except Exception as e:
        logger.error(f"Error listing volumes: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to list volumes: {str(e)}",
            'volumes': []
        }

@mcp.tool()
async def create_volume(name: str) -> Dict[str, Any]:
    """
    Create a new Docker volume.
    
    Args:
        name: Volume name
        
    Returns:
        Dictionary containing volume creation result with mount point and details
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: volume_mgr.create_volume(name)
        )
    except Exception as e:
        logger.error(f"Error creating volume {name}: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to create volume {name}: {str(e)}",
            'volume': name
        }

@mcp.tool()
async def remove_volume(name: str, force: bool = False) -> Dict[str, Any]:
    """
    Remove a Docker volume.
    
    Args:
        name: Volume name
        force: Force removal even if in use
        
    Returns:
        Dictionary containing remove operation result with status and freed space
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: volume_mgr.remove_volume(name, force)
        )
    except Exception as e:
        logger.error(f"Error removing volume {name}: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to remove volume {name}: {str(e)}",
            'volume': name,
            'force': force
        }

# SYSTEM OPERATIONS
@mcp.tool()
async def system_info() -> Dict[str, Any]:
    """
    Get Docker system information including version, containers, and resource usage.
    
    Returns:
        Dictionary containing system information including containers, images, and resource usage
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            system_mgr.system_info
        )
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to get system info: {str(e)}",
            'system_info': {}
        }

@mcp.tool()
async def docker_version() -> Dict[str, Any]:
    """
    Get Docker version information.
    
    Returns:
        Dictionary containing version information for Docker components
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            system_mgr.get_docker_version
        )
    except Exception as e:
        logger.error(f"Error getting Docker version: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to get Docker version: {str(e)}",
            'version_info': {}
        }

@mcp.tool()
async def docker_disk_usage() -> Dict[str, Any]:
    """
    Get Docker disk usage information.
    
    Returns:
        Dictionary containing disk usage information for images, containers, and volumes
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            system_mgr.get_disk_usage
        )
    except Exception as e:
        logger.error(f"Error getting Docker disk usage: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to get Docker disk usage: {str(e)}",
            'disk_usage': {}
        }

@mcp.tool()
async def docker_system_prune(
    volumes: bool = False,
    networks: bool = False,
    force: bool = False
) -> Dict[str, Any]:
    """
    Clean up unused Docker resources.
    
    Args:
        volumes: Prune volumes (default: False)
        networks: Prune networks (default: False)
        force: Don't prompt for confirmation (default: False)
        
    Returns:
        Cleanup operation result with space reclaimed
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: system_mgr.prune_system(volumes, networks, force)
        )
    except Exception as e:
        logger.error(f"Error pruning system: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to prune system: {str(e)}"
        }

# ============================================================================
# PART 2: AUSTRIAN EFFICIENCY WORKFLOW INTELLIGENCE
# Sandra's environment-specific smart tools
# ============================================================================

# STACK HEALTH INTELLIGENCE
@mcp.tool()
async def vienna_dev_status() -> Dict[str, Any]:
    """
    Sandra's complete dev environment status - Austrian efficiency style.
    One call for complete situational awareness of all stacks.
    
    Returns:
        Complete environment health with Gemütlichkeit factor
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            vienna_env.get_environment_status
        )
    except Exception as e:
        logger.error(f"Error getting Vienna dev status: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to get Vienna dev status: {str(e)}"
        }

@mcp.tool()
async def check_veogen_stack() -> Dict[str, Any]:
    """
    Complete Veogen stack health check.
    Components: backend + redis + postgres + grafana + node-exporter
    
    Returns:
        Veogen stack health with dependency analysis
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            stack_health.check_veogen_stack
        )
    except Exception as e:
        logger.error(f"Error checking Veogen stack: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to check Veogen stack: {str(e)}"
        }

@mcp.tool()
async def check_myai_health() -> Dict[str, Any]:
    """
    Health check for all MyAI projects portfolio.
    Known projects: document-viewer, calibre-plus, bob-and-alice, etc.
    
    Returns:
        MyAI projects health summary with restart loop detection
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            stack_health.check_myai_health
        )
    except Exception as e:
        logger.error(f"Error checking MyAI health: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to check MyAI health: {str(e)}"
        }

@mcp.tool()
async def check_immich_stack() -> Dict[str, Any]:
    """
    Immich photo management stack health.
    Components: server + postgres + redis + machine_learning
    
    Returns:
        Immich stack health with performance metrics
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            stack_health.check_immich_stack
        )
    except Exception as e:
        logger.error(f"Error checking Immich stack: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to check Immich stack: {str(e)}"
        }

# PROBLEM DETECTION & DIAGNOSIS
@mcp.tool()
async def find_restart_loops(threshold_minutes: int = 10) -> Dict[str, Any]:
    """
    Find containers stuck in restart loops with root cause analysis.
    Austrian efficiency: Don't just detect, understand WHY.
    
    Args:
        threshold_minutes: Time window for restart detection
        
    Returns:
        Restart loop analysis with suggested fixes
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: problem_detector.detect_restart_loops(threshold_minutes)
        )
    except Exception as e:
        logger.error(f"Error finding restart loops: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to find restart loops: {str(e)}"
        }

@mcp.tool()
async def check_frontend_health() -> Dict[str, Any]:
    """
    Sandra's insight: "frontends with no exposed ports" = broken.
    Find web frontends that should have ports but don't.
    
    Returns:
        Frontend health analysis with connectivity tests
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            problem_detector.check_frontend_health
        )
    except Exception as e:
        logger.error(f"Error checking frontend health: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to check frontend health: {str(e)}"
        }

@mcp.tool()
async def detect_dependency_issues() -> Dict[str, Any]:
    """
    Detect containers waiting for dependencies (databases, Redis, etc.)
    Focus on actual blocking relationships in Sandra's stacks.
    
    Returns:
        Dependency issue analysis with startup order recommendations
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            problem_detector.detect_dependency_issues
        )
    except Exception as e:
        logger.error(f"Error detecting dependency issues: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to detect dependency issues: {str(e)}"
        }

@mcp.tool()
async def find_missing_containers() -> Dict[str, Any]:
    """
    Detect expected containers that don't exist (like zen_goldstine).
    Knows Sandra's expected container ecosystem.
    
    Returns:
        Missing container report with recreation instructions
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            problem_detector.find_missing_containers
        )
    except Exception as e:
        logger.error(f"Error finding missing containers: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to find missing containers: {str(e)}"
        }

# INTELLIGENT AUTOMATION
@mcp.tool()
async def fix_restart_loops(container_name: str, strategy: str = "smart") -> Dict[str, Any]:
    """
    Actually fix restart loops, don't just report them.
    Strategies: restart_fresh, update_image, fix_dependencies, resource_adjust
    
    Args:
        container_name: Container with restart loop
        strategy: Fix strategy (smart, restart_fresh, update_image, fix_dependencies)
        
    Returns:
        Fix operation result with success/failure details
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: automation_mgr.fix_restart_loop(container_name, strategy)
        )
    except Exception as e:
        logger.error(f"Error fixing restart loop for {container_name}: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to fix restart loop for {container_name}: {str(e)}"
        }

@mcp.tool()
async def smart_stack_restart(stack_name: str) -> Dict[str, Any]:
    """
    Restart stacks in proper dependency order.
    Knows: Veogen, Immich, MyAI dependency chains
    
    Args:
        stack_name: Stack to restart (veogen, immich, myai)
        
    Returns:
        Stack restart result with dependency coordination
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: automation_mgr.restart_stack(stack_name)
        )
    except Exception as e:
        logger.error(f"Error restarting stack {stack_name}: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to restart stack {stack_name}: {str(e)}"
        }

@mcp.tool()
async def emergency_stack_recovery(stack_name: str) -> Dict[str, Any]:
    """
    Nuclear option: Complete stack recovery when everything is broken.
    One command for catastrophic failure recovery.
    
    Args:
        stack_name: Stack to recover (veogen, immich, myai)
        
    Returns:
        Emergency recovery result with rollback capability
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: automation_mgr.emergency_recovery(stack_name)
        )
    except Exception as e:
        logger.error(f"Error in emergency recovery for stack {stack_name}: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to perform emergency recovery for stack {stack_name}: {str(e)}"
        }

# SPECIALIZED RECOVERY
@mcp.tool()
async def zen_goldstine_recovery() -> Dict[str, Any]:
    """
    Specialized recovery for missing zen_goldstine (fetch MCP).
    Knows exactly how to recreate this critical container.
    
    Returns:
        zen_goldstine recovery result with MCP integration status
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            vienna_env.zen_goldstine_recovery
        )
    except Exception as e:
        logger.error(f"Error in zen_goldstine recovery: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to perform zen_goldstine recovery: {str(e)}"
        }

@mcp.tool()
async def find_zombie_images(age_threshold_days: int = 90) -> Dict[str, Any]:
    """
    Find old, unused images eating disk space.
    Sandra's insight: "weed out the year old zombies"
    
    Args:
        age_threshold_days: Age threshold for zombie detection
        
    Returns:
        Zombie image report with cleanup recommendations
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: problem_detector.find_zombie_images(age_threshold_days)
        )
    except Exception as e:
        logger.error(f"Error finding zombie images: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to find zombie images: {str(e)}"
        }

@mcp.tool()
async def maintenance_recommendations() -> Dict[str, Any]:
    """
    Proactive maintenance suggestions. Austrian efficiency.
    Prevent problems before they happen.
    
    Returns:
        Maintenance recommendations with priority levels
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            vienna_env.maintenance_recommendations
        )
    except Exception as e:
        logger.error(f"Error getting maintenance recommendations: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to get maintenance recommendations: {str(e)}"
        }

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
