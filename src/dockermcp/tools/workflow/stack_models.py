"""
Pydantic models for stack health monitoring and workflow tools.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field

class ComponentHealth(BaseModel):
    """Health status of a single component in a stack."""
    name: str
    type: str
    status: str
    health: str
    version: Optional[str] = None
    uptime: Optional[str] = None
    resources: Dict[str, Any] = Field(default_factory=dict)
    issues: List[Dict[str, str]] = Field(default_factory=list)

class StackHealth(BaseModel):
    """Health status of an entire stack."""
    name: str
    status: str = Field(..., description="Overall status (healthy, degraded, down)")
    components: List[ComponentHealth] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    issues: List[Dict[str, str]] = Field(default_factory=list)
    last_checked: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Timestamp of the last health check"
    )

class StackHealthResponse(BaseModel):
    """Response model for stack health checks."""
    success: bool
    message: str
    status: str = Field(..., description="Overall status (healthy, degraded, down)")
    components: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Status of individual stack components"
    )
    metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Performance and resource metrics"
    )
    issues: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of detected issues with severity and details"
    )
    last_checked: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Timestamp of the last health check"
    )
    error: Optional[str] = None

class ProjectHealth(BaseModel):
    """Health status of a project."""
    name: str
    status: str
    health: str
    version: Optional[str] = None
    uptime: Optional[str] = None
    issues: List[Dict[str, str]] = Field(default_factory=list)

class ProjectHealthResponse(BaseModel):
    """Response model for project health checks."""
    success: bool
    message: str
    projects: List[ProjectHealth] = []
    overall_status: str = Field(
        ...,
        description="Aggregated health status across all projects"
    )
    metrics: Dict[str, Any] = {}
    error: Optional[str] = None

class StackOperationResponse(BaseModel):
    """Response model for stack operations."""
    success: bool
    message: str
    stack: str
    operation: str
    details: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None

class IssueSeverity(str):
    """Severity levels for detected issues."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class DetectedIssue(BaseModel):
    """A detected issue with a container or service."""
    component: str
    severity: IssueSeverity
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    suggested_fixes: List[str] = Field(default_factory=list)
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )

class RecoveryOptions(BaseModel):
    """Options for stack recovery operations."""
    force: bool = False
    backup_first: bool = True
    include_dependencies: bool = True
    timeout_seconds: int = 300
    rollback_on_failure: bool = True
