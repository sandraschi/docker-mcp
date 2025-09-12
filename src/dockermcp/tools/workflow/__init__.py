"""
Workflow management and automation tools for Docker MCP.

This module provides FastMCP 2.12.0+ compatible tools for workflow automation,
stack health monitoring, problem detection, and recovery operations.
"""
from typing import List, Dict, Any, Optional, Callable

# Import models
from .stack_models import (
    StackHealthResponse,
    ProjectHealthResponse,
    StackOperationResponse,
    RecoveryOptions,
    IssueSeverity,
    DetectedIssue,
    ComponentHealth,
    StackHealth
)

# Import stack health tools
from .stack_health import (
    check_stack_health,
    check_veogen_stack,
    check_immich_stack,
    check_myai_health,
    stack_health_checker
)

# Import problem detection tools
from .problem_detection import (
    find_restart_loops,
    detect_dependency_issues,
    find_missing_containers,
    problem_detector
)

# Import recovery tools
from .recovery import (
    fix_restart_loops,
    smart_stack_restart,
    emergency_stack_recovery,
    stack_recovery
)

# Tools are automatically discovered by the @Tool decorator
# No need for explicit get_tools() function anymore
# Export all tools and models for easy importing
__all__ = [
    # Models
    'StackHealthResponse',
    'ProjectHealthResponse',
    'StackOperationResponse',
    'RecoveryOptions',
    'IssueSeverity',
    'DetectedIssue',
    'ComponentHealth',
    'StackHealth',
    
    # Core components
    'stack_health_checker',
    'problem_detector',
    'stack_recovery',
    'get_tools',
    
    # Health check functions
    'check_stack_health',
    'check_veogen_stack',
    'check_immich_stack',
    'check_myai_health',
    
    # Problem detection functions
    'find_restart_loops',
    'detect_dependency_issues',
    'find_missing_containers',
    
    # Recovery functions
    'fix_restart_loops',
    'smart_stack_restart',
    'emergency_stack_recovery'
]
