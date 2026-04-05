"""
Service health check validators and utilities.

This module provides validators and utilities for checking the health of services
in a workflow, including HTTP health checks, command-based checks, and custom checkers.
"""
from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from datetime import datetime
from enum import StrEnum
from typing import (
    Any,
    TypeVar,
)

import httpx
from pydantic import BaseModel, Field, HttpUrl, field_validator

from .models import (
    BaseModel,
    ServiceDefinition,
    ServiceHealth,
)

T = TypeVar('T')

class HealthCheckType(StrEnum):
    """Types of health checks supported for services."""
    COMMAND = "command"
    HTTP = "http"
    TCP = "tcp"
    GRPC = "grpc"
    EXEC = "exec"
    CUSTOM = "custom"


class HealthCheckResult(BaseModel):
    """Result of a health check execution."""
    status: ServiceHealth = Field(
        default=ServiceHealth.UNKNOWN,
        description="The health status of the service"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the health check was performed"
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional details about the health check result"
    )
    error: str | None = Field(
        None,
        description="Error message if the health check failed"
    )
    duration_ms: float = Field(
        0.0,
        description="How long the health check took in milliseconds"
    )

    @classmethod
    def healthy(cls, **kwargs: Any) -> HealthCheckResult:
        """Create a healthy result."""
        return cls(status=ServiceHealth.HEALTHY, **kwargs)

    @classmethod
    def unhealthy(cls, error: str, **kwargs: Any) -> HealthCheckResult:
        """Create an unhealthy result with an error message."""
        return cls(
            status=ServiceHealth.UNHEALTHY,
            error=error,
            **kwargs
        )

    @classmethod
    def from_exception(cls, exc: Exception, **kwargs: Any) -> HealthCheckResult:
        """Create a result from an exception."""
        return cls.unhealthy(
            error=str(exc) or exc.__class__.__name__,
            details={"exception": exc.__class__.__name__},
            **kwargs
        )


class BaseHealthCheck[T](BaseModel):
    """Base class for all health check implementations."""
    name: str = Field(
        ...,
        description="Unique name for this health check"
    )
    check_type: HealthCheckType = Field(
        ...,
        description="Type of health check"
    )
    interval: int = Field(
        30,
        ge=1,
        description="Interval between checks in seconds"
    )
    timeout: int = Field(
        10,
        ge=1,
        description="Timeout for the check in seconds"
    )
    retries: int = Field(
        3,
        ge=0,
        description="Number of retries before marking as unhealthy"
    )
    start_period: int = Field(
        0,
        ge=0,
        description="Initial delay before starting health checks in seconds"
    )

    async def execute(self) -> HealthCheckResult:
        """Execute the health check and return the result.

        Subclasses must implement this method to perform the actual health check.
        """
        start_time = time.monotonic()
        result = HealthCheckResult(status=ServiceHealth.UNKNOWN)

        try:
            # Execute the check with retries
            for attempt in range(1, self.retries + 1):
                try:
                    check_result = await self._execute_check()
                    if check_result.status in (ServiceHealth.HEALTHY, ServiceHealth.DEGRADED):
                        return check_result

                    # If we have retries left, wait before trying again
                    if attempt < self.retries:
                        await asyncio.sleep(min(1, self.timeout / 2))
                except Exception:
                    if attempt == self.retries:
                        raise
                    await asyncio.sleep(min(1, self.timeout / 2))

            # If we get here, all retries failed
            return HealthCheckResult(
                status=ServiceHealth.UNHEALTHY,
                error=f"Health check failed after {self.retries} attempts"
            )

        except Exception as e:
            return HealthCheckResult.from_exception(e)
        finally:
            result.duration_ms = (time.monotonic() - start_time) * 1000

    async def _execute_check(self) -> HealthCheckResult:
        """Perform the actual health check logic.

        Subclasses must implement this method.
        """
        raise NotImplementedError("Subclasses must implement _execute_check")


class CommandHealthCheck(BaseHealthCheck):
    """Health check that runs a command in the container."""
    command: list[str] = Field(
        ...,
        min_length=1,
        description="Command to run in the container"
    )

    check_type: HealthCheckType = Field(
        default=HealthCheckType.COMMAND,
        frozen=True
    )

    async def _execute_check(self) -> HealthCheckResult:
        # In a real implementation, this would execute the command in the container
        # For now, we'll simulate a successful check
        return HealthCheckResult.healthy(
            details={"command": self.command}
        )


class HTTPHealthCheck(BaseHealthCheck):
    """Health check that makes an HTTP request to a service endpoint."""
    url: HttpUrl = Field(
        ...,
        description="URL to check (e.g., http://localhost:8080/health)"
    )
    method: str = Field(
        "GET",
        pattern=r'^(GET|POST|PUT|DELETE|HEAD|OPTIONS|PATCH)$',
        description="HTTP method to use"
    )
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="HTTP headers to include in the request"
    )
    body: dict[str, Any] | None = Field(
        None,
        description="Request body (for POST/PUT/PATCH)"
    )
    expected_status: list[int] = Field(
        [200],
        description="List of HTTP status codes that indicate success"
    )

    check_type: HealthCheckType = Field(
        default=HealthCheckType.HTTP,
        frozen=True
    )

    @field_validator('url', mode='before')
    @classmethod
    def validate_url(cls, v: Any) -> HttpUrl:
        """Ensure the URL is valid and has a scheme."""
        if isinstance(v, str):
            if not v.startswith(('http://', 'https://')):
                v = f'http://{v}'
        return v

    async def _execute_check(self) -> HealthCheckResult:
        """Execute an HTTP health check."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(
                    method=self.method,
                    url=str(self.url),
                    headers=self.headers,
                    json=self.body
                )

                is_healthy = response.status_code in self.expected_status

                try:
                    response_data = response.json()
                except ValueError:
                    response_data = response.text

                return HealthCheckResult(
                    status=ServiceHealth.HEALTHY if is_healthy else ServiceHealth.UNHEALTHY,
                    details={
                        "status_code": response.status_code,
                        "response": response_data,
                        "headers": dict(response.headers)
                    },
                    error=None if is_healthy else f"Unexpected status code: {response.status_code}"
                )

            except httpx.RequestError as e:
                return HealthCheckResult.unhealthy(
                    f"Request failed: {str(e) or e.__class__.__name__}",
                    details={"error_type": e.__class__.__name__}
                )


class TCPHealthCheck(BaseHealthCheck):
    """Health check that attempts to establish a TCP connection."""
    host: str = Field(
        "localhost",
        description="Host to connect to"
    )
    port: int = Field(
        ...,
        ge=1,
        le=65535,
        description="Port to connect to"
    )

    check_type: HealthCheckType = Field(
        default=HealthCheckType.TCP,
        frozen=True
    )

    async def _execute_check(self) -> HealthCheckResult:
        """Execute a TCP health check."""
        try:
            # Use asyncio's open_connection with a timeout
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout
            )
            writer.close()
            await writer.wait_closed()
            return HealthCheckResult.healthy()

        except (TimeoutError, ConnectionRefusedError, OSError) as e:
            return HealthCheckResult.unhealthy(
                f"TCP connection failed: {str(e) or e.__class__.__name__}",
                details={"error_type": e.__class__.__name__}
            )


class CustomHealthCheck(BaseHealthCheck):
    """Health check that uses a custom check function."""
    check_func: str = Field(
        ...,
        description="Import path to a function that performs the health check"
    )

    check_type: HealthCheckType = Field(
        default=HealthCheckType.CUSTOM,
        frozen=True
    )

    _func: Callable[..., Awaitable[HealthCheckResult]] | None = None

    async def _execute_check(self) -> HealthCheckResult:
        """Execute a custom health check function."""
        if self._func is None:
            try:
                # Import the function dynamically
                module_path, func_name = self.check_func.rsplit('.', 1)
                module = __import__(module_path, fromlist=[func_name])
                self._func = getattr(module, func_name)
            except (ImportError, AttributeError, ValueError) as e:
                return HealthCheckResult.unhealthy(
                    f"Failed to import check function: {e}"
                )

        try:
            return await self._func()
        except Exception as e:
            return HealthCheckResult.from_exception(e)


class HealthChecker:
    """Manages health checks for services."""

    def __init__(self):
        self.checks: dict[str, BaseHealthCheck] = {}
        self.results: dict[str, HealthCheckResult] = {}
        self.tasks: dict[str, asyncio.Task] = {}

    def add_check(self, check: BaseHealthCheck) -> None:
        """Add a health check to be monitored."""
        self.checks[check.name] = check
        if check.name not in self.results:
            self.results[check.name] = HealthCheckResult(
                status=ServiceHealth.STARTING
            )

    async def start(self) -> None:
        """Start all health checks."""
        for check in self.checks.values():
            self.tasks[check.name] = asyncio.create_task(
                self._run_check(check)
            )

    async def stop(self) -> None:
        """Stop all health checks."""
        for task in self.tasks.values():
            task.cancel()
        await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        self.tasks.clear()

    def get_status(self, name: str) -> HealthCheckResult | None:
        """Get the current status of a health check."""
        return self.results.get(name)

    def get_overall_status(self) -> ServiceHealth:
        """Get the overall health status."""
        if not self.results:
            return ServiceHealth.UNKNOWN

        statuses = [result.status for result in self.results.values()]

        if ServiceHealth.UNHEALTHY in statuses:
            return ServiceHealth.UNHEALTHY
        elif ServiceHealth.DEGRADED in statuses:
            return ServiceHealth.DEGRADED
        elif all(s == ServiceHealth.HEALTHY for s in statuses):
            return ServiceHealth.HEALTHY
        elif any(s == ServiceHealth.STARTING for s in statuses):
            return ServiceHealth.STARTING
        else:
            return ServiceHealth.UNKNOWN

    async def _run_check(self, check: BaseHealthCheck) -> None:
        """Run a health check in a loop."""
        # Initial delay if specified
        if check.start_period > 0:
            await asyncio.sleep(check.start_period)

        while True:
            try:
                result = await check.execute()
                self.results[check.name] = result
            except asyncio.CancelledError:
                # Task was cancelled
                break
            except Exception as e:
                self.results[check.name] = HealthCheckResult.from_exception(e)

            # Wait for the next check interval
            await asyncio.sleep(check.interval)


# Factory function to create the appropriate health check
def create_health_check(config: dict[str, Any]) -> BaseHealthCheck:
    """Create a health check from a configuration dictionary."""
    check_type = HealthCheckType(config.get('type', 'command').lower())

    if check_type == HealthCheckType.HTTP:
        return HTTPHealthCheck(**config)
    elif check_type == HealthCheckType.TCP:
        return TCPHealthCheck(**config)
    elif check_type == HealthCheckType.COMMAND:
        return CommandHealthCheck(**config)
    elif check_type == HealthCheckType.CUSTOM:
        return CustomHealthCheck(**config)
    else:
        raise ValueError(f"Unsupported health check type: {check_type}")


def health_check_from_service(service: ServiceDefinition) -> BaseHealthCheck | None:
    """Create a health check from a service definition."""
    if not service.health_check:
        return None

    config = service.health_check.copy()

    # Determine the check type based on the configuration
    if 'test' in config and isinstance(config['test'], list):
        if config['test'][0].upper() in ('CMD', 'CMD-SHELL'):
            return CommandHealthCheck(
                name=f"{service.name}-cmd-check",
                command=config['test'][1:],
                interval=config.get('interval', 30),
                timeout=config.get('timeout', 10),
                retries=config.get('retries', 3),
                start_period=config.get('start_period', 0)
            )

    # Default to HTTP check if a URL is provided
    if 'url' in config or 'port' in config:
        return HTTPHealthCheck(
            name=f"{service.name}-http-check",
            url=config.get('url', f"http://localhost:{config.get('port', 80)}/health"),
            method=config.get('method', 'GET'),
            headers=config.get('headers', {}),
            expected_status=config.get('expected_status', [200]),
            interval=config.get('interval', 30),
            timeout=config.get('timeout', 10),
            retries=config.get('retries', 3),
            start_period=config.get('start_period', 0)
        )

    # Fall back to TCP check if only a port is specified
    if 'port' in config:
        return TCPHealthCheck(
            name=f"{service.name}-tcp-check",
            port=config['port'],
            interval=config.get('interval', 30),
            timeout=config.get('timeout', 10),
            retries=config.get('retries', 3),
            start_period=config.get('start_period', 0)
        )

    return None
