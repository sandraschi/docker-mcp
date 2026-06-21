"""
Alert Management Tools for Monitoring Stack

This module provides tools to manage alerts and notifications in the monitoring stack.
"""

import json
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from dockermcp.logging_config import logger
from dockermcp.mcp_instance import mcp

# Path to alert rules
alert_rules_dir = Path(__file__).parent.parent.parent.parent.parent / "monitoring" / "prometheus" / "alert.rules"


def ensure_alert_rules_dir() -> bool:
    """Ensure the alert rules directory exists."""
    try:
        alert_rules_dir.parent.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Failed to create alert rules directory: {e}")
        return False


class AlertRule(BaseModel):
    """Model representing an alert rule."""

    name: str = Field(..., description="Name of the alert")
    expr: str = Field(..., description="PromQL expression for the alert")
    for_duration: str = Field("5m", description="Duration the condition must be true before firing")
    severity: str = Field("warning", description="Severity level (critical, warning, info)")
    summary: str | None = Field(None, description="Short description of the alert")
    description: str | None = Field(None, description="Detailed description of the alert")
    labels: dict[str, str] = Field(default_factory=dict, description="Additional labels for the alert")
    annotations: dict[str, str] = Field(default_factory=dict, description="Additional annotations for the alert")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "HighCPUUsage",
                "expr": '100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m]))) * 100 > 80',
                "for_duration": "5m",
                "severity": "warning",
                "summary": "High CPU usage on {{ $labels.instance }}",
                "description": "CPU usage is {{ $value }}% on {{ $labels.instance }}",
            }
        }
    )


class ListAlertRulesParams(BaseModel):
    """Parameters for listing alert rules."""

    format: Literal["json", "yaml", "text"] = Field("json", description="Output format for the alert rules")


@mcp.tool
async def list_alert_rules(params: ListAlertRulesParams) -> dict[str, Any]:
    """
    List all configured alert rules.

    Args:
        format: Output format (json, yaml, or text)

    Returns:
        Dictionary with the alert rules in the specified format

    Example:
        >>> await list_alert_rules(format='json')
        {
            'status': 'success',
            'alerts': [
                {
                    'name': 'HighCPUUsage',
                    'expr': '100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100 > 80',
                    'for': '5m',
                    'labels': {'severity': 'warning'},
                    'annotations': {
                        'summary': 'High CPU usage on {{ $labels.instance }}',
                        'description': 'CPU usage is {{ $value }}% on {{ $labels.instance }}'
                    }
                }
            ]
        }
    """
    try:
        alerts = []

        if not alert_rules_dir.exists():
            logger.info("No alert rules file found at %s", alert_rules_dir)
            return {"status": "success", "message": "No alert rules configured", "alerts": []}

        try:
            # Load alert rules from file
            with open(alert_rules_dir) as f:
                rules = yaml.safe_load(f) or {}

            # Extract alert rules
            for group in rules.get("groups", []):
                for rule in group.get("rules", []):
                    if "alert" in rule:
                        alerts.append(
                            AlertRule(
                                name=rule["alert"],
                                expr=rule.get("expr", ""),
                                for_duration=rule.get("for", "5m"),
                                severity=rule.get("labels", {}).get("severity", "warning"),
                                summary=rule.get("annotations", {}).get("summary"),
                                description=rule.get("annotations", {}).get("description"),
                                labels=rule.get("labels", {}),
                                annotations=rule.get("annotations", {}),
                            )
                        )
        except yaml.YAMLError as e:
            logger.error("Failed to parse alert rules file: %s", str(e))
            return {"status": "error", "error": f"Invalid alert rules file: {e!s}"}

        # Format the output
        output = ""
        alerts_dict = [alert.dict(exclude_none=True) for alert in alerts]

        if params.format == "yaml":
            output = yaml.dump({"alerts": alerts_dict}, default_flow_style=False)
        elif params.format == "text":
            for alert in alerts:
                output += f"=== {alert.name} ===\n"
                output += f"Expression: {alert.expr}\n"
                if alert.for_duration:
                    output += f"For: {alert.for_duration}\n"
                if alert.labels:
                    output += f"Labels: {json.dumps(alert.labels, indent=2)}\n"
                if alert.annotations:
                    output += f"Annotations: {json.dumps(alert.annotations, indent=2)}\n"
                output += "\n"
        else:  # json
            output = json.dumps({"alerts": alerts_dict}, indent=2)

        return {
            "status": "success",
            "alerts": alerts_dict,
            "output": output if params.format != "json" else json.loads(output),
        }
    except Exception as e:
        error_msg = f"Failed to list alert rules: {e!s}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}


class AddAlertRuleParams(AlertRule):
    """Parameters for adding a new alert rule."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "HighCPUUsage",
                "expr": '100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m]))) * 100 > 80',
                "for_duration": "5m",
                "severity": "warning",
                "summary": "High CPU usage on {{ $labels.instance }}",
                "description": "CPU usage is {{ $value }}% on {{ $labels.instance }}",
            }
        }
    )


@mcp.tool
async def add_alert_rule(params: AddAlertRuleParams) -> dict[str, Any]:
    """
    Add a new alert rule to the monitoring stack.

    Args:
        name: Name of the alert
        expr: PromQL expression for the alert
        for_duration: Duration the condition must be true before firing
        severity: Severity level (critical, warning, info)
        summary: Short description of the alert
        description: Detailed description of the alert
        labels: Additional labels for the alert
        annotations: Additional annotations for the alert

    Returns:
        Dictionary with the result of the operation

    Example:
        >>> await add_alert_rule(
        ...     name="HighCPUUsage",
        ...     expr="100 - (avg by(instance) (rate(node_cpu_seconds_total{mode=\"idle\"}[5m]))) * 100 > 80",
        ...     for_duration="5m",
        ...     severity="warning",
        ...     summary="High CPU usage on {{ $labels.instance }}",
        ...     description="CPU usage is {{ $value }}% on {{ $labels.instance }}"
        ... )
        {
            'status': 'success',
            'message': 'Alert rule added',
            'alert': {
                'name': 'HighCPUUsage',
                'expr': '100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m]))) * 100 > 80',
                'for': '5m',
                'labels': {'severity': 'warning'},
                'annotations': {
                    'summary': 'High CPU usage on {{ $labels.instance }}',
                    'description': 'CPU usage is {{ $value }}% on {{ $labels.instance }}'
                }
            }
        }
    """
    try:
        if not ensure_alert_rules_dir():
            error_msg = "Failed to create alert rules directory"
            logger.error(error_msg)
            return {"status": "error", "error": error_msg}

        # Create the new alert rule
        new_alert = {
            "alert": params.name,
            "expr": params.expr,
            "for": params.for_duration,
            "labels": {"severity": params.severity, **params.labels},
            "annotations": {},
        }

        if params.summary:
            new_alert["annotations"]["summary"] = params.summary
        if params.description:
            new_alert["annotations"]["description"] = params.description
        if params.annotations:
            new_alert["annotations"].update(params.annotations)

        # Load existing rules
        rules = {"groups": [{"name": "docker-mcp", "rules": []}]}
        if alert_rules_dir.exists():
            try:
                with open(alert_rules_dir) as f:
                    rules = yaml.safe_load(f) or rules
            except yaml.YAMLError as e:
                error_msg = f"Failed to load existing alert rules: {e!s}"
                logger.error(error_msg)
                return {"status": "error", "error": error_msg}

        # Check if alert with same name already exists
        alert_updated = False
        for group in rules.get("groups", []):
            for i, rule in enumerate(group.get("rules", [])):
                if rule.get("alert") == params.name:
                    group["rules"][i] = new_alert  # Update existing
                    alert_updated = True
                    break

            if not alert_updated:
                group.setdefault("rules", []).append(new_alert)  # Add new

        # Save back to file
        try:
            with open(alert_rules_dir, "w") as f:
                yaml.dump(rules, f, default_flow_style=False)

            logger.info(f"Alert rule '{params.name}' {'updated' if alert_updated else 'added'}")
            return {
                "status": "success",
                "message": f"Alert rule {params.name} {'updated' if alert_updated else 'added'}",
                "alert": params.name,
                "updated": alert_updated,
            }
        except OSError as e:
            error_msg = f"Failed to save alert rules: {e!s}"
            logger.error(error_msg)
            return {"status": "error", "error": error_msg}
    except Exception as e:
        error_msg = f"Failed to add alert rule: {e!s}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}


class RemoveAlertRuleParams(BaseModel):
    """Parameters for removing an alert rule."""

    name: str = Field(..., description="Name of the alert rule to remove")


@mcp.tool
async def remove_alert_rule(params: RemoveAlertRuleParams) -> dict[str, Any]:
    """
    Remove an alert rule by name.

    Args:
        name: Name of the alert rule to remove

    Returns:
        Dictionary with the result of the operation

    Example:
        >>> await remove_alert_rule("HighCPUUsage")
        {
            'status': 'success',
            'message': 'Alert rule removed',
            'removed_alert': 'HighCPUUsage'
        }
    """
    try:
        if not alert_rules_dir.exists():
            error_msg = "No alert rules configured"
            logger.warning(error_msg)
            return {"status": "error", "error": error_msg}

        # Load existing rules
        try:
            with open(alert_rules_dir) as f:
                rules = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            error_msg = f"Failed to load alert rules: {e!s}"
            logger.error(error_msg)
            return {"status": "error", "error": error_msg}

        # Find and remove the alert
        removed = False
        for group in rules.get("groups", []):
            if "rules" in group:
                original_count = len(group["rules"])
                group["rules"] = [r for r in group["rules"] if r.get("alert") != params.name]
                if len(group["rules"]) < original_count:
                    removed = True

        if not removed:
            error_msg = f"Alert rule '{params.name}' not found"
            logger.warning(error_msg)
            return {"status": "error", "error": error_msg}

        # Save back to file
        try:
            with open(alert_rules_dir, "w") as f:
                yaml.dump(rules, f, default_flow_style=False)

            logger.info(f"Alert rule '{params.name}' removed")
            return {"status": "success", "message": "Alert rule removed", "removed_alert": params.name}
        except OSError as e:
            error_msg = f"Failed to save alert rules: {e!s}"
            logger.error(error_msg)
            return {"status": "error", "error": error_msg}
    except Exception as e:
        error_msg = f"Failed to remove alert rule: {e!s}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}
