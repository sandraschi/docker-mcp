"""
Workflow validators for dependencies and constraints.

This module contains validators for ensuring workflow integrity, including
service dependencies, resource constraints, and workflow state transitions.
"""

import re
from datetime import datetime
from typing import Any, ClassVar, TypeVar

from .models import ServiceDefinition, WorkflowResponse, WorkflowStatus

# Type variable for generic validator classes
T = TypeVar("T")


class ValidationError(Exception):
    """Base exception for validation errors."""

    pass


class DependencyError(ValidationError):
    """Raised when there are issues with service dependencies."""

    pass


class ConstraintError(ValidationError):
    """Raised when constraints are violated."""

    pass


class WorkflowValidator[T]:
    """Base class for workflow validators."""

    def validate(self, value: T) -> T:
        """Validate the input value.

        Args:
            value: The value to validate

        Returns:
            The validated value

        Raises:
            ValidationError: If validation fails
        """
        return value


class ServiceDependencyValidator(WorkflowValidator[dict[str, ServiceDefinition]]):
    """Validator for service dependencies in a workflow.

    Ensures that:
    1. All service dependencies exist
    2. There are no circular dependencies
    3. Dependencies form a valid DAG (Directed Acyclic Graph)
    """

    def validate(self, services: dict[str, ServiceDefinition]) -> dict[str, ServiceDefinition]:
        """Validate service dependencies.

        Args:
            services: Dictionary of service name to ServiceDefinition

        Returns:
            The input services if validation passes

        Raises:
            DependencyError: If there are invalid dependencies
        """
        self._validate_dependency_existence(services)
        self._check_for_cycles(services)
        return services

    def _validate_dependency_existence(self, services: dict[str, ServiceDefinition]) -> None:
        """Ensure all dependencies reference existing services."""
        service_names = set(services.keys())

        for service_name, service in services.items():
            for dep in service.depends_on:
                if dep not in service_names:
                    raise DependencyError(f"Service '{service_name}' depends on non-existent service '{dep}'")

    def _check_for_cycles(self, services: dict[str, ServiceDefinition]) -> None:
        """Check for circular dependencies using depth-first search."""
        visited = set()
        recursion_stack = set()

        def visit(service_name: str, path: list[str]) -> None:
            if service_name in recursion_stack:
                cycle = " -> ".join([*path[path.index(service_name) :], service_name])
                raise DependencyError(f"Circular dependency detected: {cycle}")

            if service_name in visited:
                return

            visited.add(service_name)
            recursion_stack.add(service_name)

            service = services[service_name]
            for dep in service.depends_on:
                visit(dep, [*path, service_name])

            recursion_stack.remove(service_name)

        for service_name in services:
            if service_name not in visited:
                visit(service_name, [])


class ResourceConstraintValidator(WorkflowValidator[dict[str, ServiceDefinition]]):
    """Validator for resource constraints in a workflow.

    Ensures that:
    1. Resource limits are within allowed bounds
    2. Total resource usage doesn't exceed cluster capacity
    3. Resource requests don't exceed limits
    """

    def __init__(self, max_cpu: float = 16.0, max_memory: str = "64Gi", max_services: int = 100):
        """Initialize the validator with cluster constraints.

        Args:
            max_cpu: Maximum CPU cores per node
            max_memory: Maximum memory per node (e.g., '64Gi')
            max_services: Maximum number of services per workflow
        """
        self.max_cpu = max_cpu
        self.max_memory = self._parse_memory(max_memory)
        self.max_services = max_services

    def validate(self, services: dict[str, ServiceDefinition]) -> dict[str, ServiceDefinition]:
        """Validate resource constraints.

        Args:
            services: Dictionary of service name to ServiceDefinition

        Returns:
            The input services if validation passes

        Raises:
            ConstraintError: If resource constraints are violated
        """
        if len(services) > self.max_services:
            raise ConstraintError(f"Workflow exceeds maximum number of services: {len(services)} > {self.max_services}")

        for service_name, service in services.items():
            self._validate_service_resources(service_name, service)

        return services

    def _validate_service_resources(self, service_name: str, service: ServiceDefinition) -> None:
        """Validate resource constraints for a single service."""
        resources = service.resources or {}
        limits = resources.get("limits", {})
        requests = resources.get("requests", {})

        # Check CPU limits
        if "cpu" in limits:
            cpu = self._parse_cpu(limits["cpu"])
            if cpu > self.max_cpu:
                raise ConstraintError(
                    f"Service '{service_name}' CPU limit ({cpu}) exceeds maximum allowed ({self.max_cpu})"
                )

            # Ensure requests don't exceed limits
            if "cpu" in requests:
                req_cpu = self._parse_cpu(requests["cpu"])
                if req_cpu > cpu:
                    raise ConstraintError(f"Service '{service_name}' CPU request ({req_cpu}) exceeds limit ({cpu})")

        # Check memory limits
        if "memory" in limits:
            memory = self._parse_memory(limits["memory"])
            if memory > self.max_memory:
                raise ConstraintError(
                    f"Service '{service_name}' memory limit ({self._format_memory(memory)}) "
                    f"exceeds maximum allowed ({self._format_memory(self.max_memory)})"
                )

            # Ensure requests don't exceed limits
            if "memory" in requests:
                req_memory = self._parse_memory(requests["memory"])
                if req_memory > memory:
                    raise ConstraintError(
                        f"Service '{service_name}' memory request ({self._format_memory(req_memory)}) "
                        f"exceeds limit ({self._format_memory(memory)})"
                    )

    @staticmethod
    def _parse_cpu(cpu: Any) -> float:
        """Parse CPU string to float (e.g., '500m' -> 0.5)."""
        if isinstance(cpu, (int, float)):
            return float(cpu)

        if isinstance(cpu, str):
            if cpu.endswith("m"):
                return float(cpu[:-1]) / 1000
            return float(cpu)

        raise ValueError(f"Invalid CPU value: {cpu}")

    @staticmethod
    def _parse_memory(memory: Any) -> int:
        """Parse memory string to bytes (e.g., '1Gi' -> 1073741824)."""
        if isinstance(memory, (int, float)):
            return int(memory)

        if not isinstance(memory, str):
            raise ValueError(f"Invalid memory value: {memory}")

        # Normalize the input
        memory = memory.upper().strip()

        # Special case for '64GI' format (uppercase I)
        if memory.endswith("GI"):
            memory = memory.replace("GI", "G")

        # Parse numeric part and unit
        match = re.match(r"^(\d+)([KMGTP]?[iI]?[bB]?|[bB])?$", memory)
        if not match:
            raise ValueError(f"Invalid memory format: {memory}")

        value = int(match.group(1))
        unit = (match.group(2) or "").upper().replace("B", "").replace("I", "i")

        # Handle case-insensitive units
        if unit == "I":
            unit = "i"

        # Convert to bytes
        units = {
            "": 1,  # bytes
            "i": 1,  # bytes (case-insensitive)
            "K": 1000,  # kilobytes
            "M": 1000**2,  # megabytes
            "G": 1000**3,  # gigabytes
            "T": 1000**4,  # terabytes
            "P": 1000**5,  # petabytes
            "KI": 1024,  # kibibytes
            "MI": 1024**2,  # mebibytes
            "GI": 1024**3,  # gibibytes
            "TI": 1024**4,  # tebibytes
            "PI": 1024**5,  # pebibytes
        }

        return value * units[unit]

    @staticmethod
    def _format_memory(bytes_val: int) -> str:
        """Format bytes to human-readable string."""
        for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei"]:  # noqa: B007
            if bytes_val < 1024:
                break
            bytes_val /= 1024

        return f"{bytes_val:.1f}{unit}" if unit else f"{bytes_val}B"


class WorkflowStateValidator(WorkflowValidator[WorkflowResponse]):
    """Validator for workflow state transitions.

    Ensures that workflow state transitions are valid according to the
    workflow's current state and the requested transition.
    """

    # Valid state transitions: {from_state: {to_state1, to_state2, ...}}
    VALID_TRANSITIONS: ClassVar[dict] = {
        WorkflowStatus.PENDING: {WorkflowStatus.RUNNING, WorkflowStatus.PAUSED, WorkflowStatus.CANCELLED},
        WorkflowStatus.RUNNING: {
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.PAUSED,
            WorkflowStatus.CANCELLED,
            WorkflowStatus.RETRYING,
        },
        WorkflowStatus.PAUSED: {WorkflowStatus.RUNNING, WorkflowStatus.CANCELLED},
        WorkflowStatus.RETRYING: {WorkflowStatus.RUNNING, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED},
        # Terminal states (no valid transitions from these)
        WorkflowStatus.COMPLETED: set(),
        WorkflowStatus.FAILED: set(),
        WorkflowStatus.CANCELLED: set(),
        WorkflowStatus.TIMED_OUT: set(),
        WorkflowStatus.SKIPPED: set(),
    }

    def validate(self, current: WorkflowResponse, new_status: WorkflowStatus) -> WorkflowResponse:
        """Validate a workflow state transition.

        Args:
            current: Current workflow state
            new_status: Requested new status

        Returns:
            The updated workflow state if the transition is valid

        Raises:
            ConstraintError: If the state transition is invalid
        """
        current_status = WorkflowStatus(current.status)

        if new_status not in self.VALID_TRANSITIONS.get(current_status, set()):
            raise ConstraintError(f"Invalid state transition: {current_status} -> {new_status}")

        # Update the workflow status and timestamp
        current.status = new_status
        current.updated_at = datetime.utcnow()

        return current


class WorkflowValidatorChain(WorkflowValidator[T]):
    """Chain multiple validators together."""

    def __init__(self, *validators: WorkflowValidator[T]):
        """Initialize with a sequence of validators."""
        self.validators = validators

    def validate(self, value: T) -> T:
        """Apply all validators in sequence."""
        for validator in self.validators:
            value = validator.validate(value)
        return value


# Common validator instances
SERVICE_DEPENDENCY_VALIDATOR = ServiceDependencyValidator()
RESOURCE_CONSTRAINT_VALIDATOR = ResourceConstraintValidator()
WORKFLOW_STATE_VALIDATOR = WorkflowStateValidator()

# Validator for new workflows
WORKFLOW_VALIDATOR = WorkflowValidatorChain(SERVICE_DEPENDENCY_VALIDATOR, RESOURCE_CONSTRAINT_VALIDATOR)
