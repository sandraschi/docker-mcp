"""
Alert Management Tools for Monitoring Stack

This module provides tools to manage alerts and notifications in the monitoring stack.
"""
import json
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path

from fastmcp.tools import Tool
from dockermcp.logging_config import logger

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

@Tool(
    name="list_alert_rules",
    description="List all configured alert rules",
    parameters={
        'type': 'object',
        'properties': {
            'format': {
                'type': 'string',
                'enum': ['json', 'yaml', 'text'],
                'default': 'json',
                'description': 'Output format for the alert rules'
            }
        }
    }
)
async def list_alert_rules(format: str = 'json') -> Dict[str, Any]:
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
        if not alert_rules_dir.exists():
            return {
                "status": "success",
                "message": "No alert rules configured",
                "alerts": []
            }
        
        alerts = []
        # Load alert rules from file
        with open(alert_rules_dir, 'r') as f:
            rules = yaml.safe_load(f) or {}
        
        # Extract alert rules
        for group in rules.get('groups', []):
            for rule in group.get('rules', []):
                if 'alert' in rule:
                    alerts.append({
                        'name': rule['alert'],
                        'expr': rule.get('expr', ''),
                        'for': rule.get('for', ''),
                        'labels': rule.get('labels', {}),
                        'annotations': rule.get('annotations', {})
                    })
        
        # Format the output
        if format == 'yaml':
            output = yaml.dump({"alerts": alerts}, default_flow_style=False)
        elif format == 'text':
            output = ""
            for alert in alerts:
                output += f"=== {alert['name']} ===\n"
                output += f"Expression: {alert['expr']}\n"
                if alert.get('for'):
                    output += f"For: {alert['for']}\n"
                if alert.get('labels'):
                    output += f"Labels: {json.dumps(alert['labels'], indent=2)}\n"
                if alert.get('annotations'):
                    output += f"Annotations: {json.dumps(alert['annotations'], indent=2)}\n"
                output += "\n"
        else:  # json
            output = json.dumps({"alerts": alerts}, indent=2)
        
        return {
            "status": "success",
            "alerts": alerts,
            "output": output if format != 'json' else json.loads(output)
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to list alert rules: {str(e)}"
        }

@Tool(
    name="add_alert_rule",
    description="Add a new alert rule",
    parameters={
        'type': 'object',
        'properties': {
            'name': {
                'type': 'string',
                'description': 'Name of the alert'
            },
            'expr': {
                'type': 'string',
                'description': 'PromQL expression for the alert'
            },
            'for': {
                'type': 'string',
                'default': '5m',
                'description': 'Duration the condition must be true before firing'
            },
            'severity': {
                'type': 'string',
                'enum': ['critical', 'warning', 'info'],
                'default': 'warning',
                'description': 'Severity level of the alert'
            },
            'summary': {
                'type': 'string',
                'description': 'Short description of the alert'
            },
            'description': {
                'type': 'string',
                'description': 'Detailed description of the alert'
            },
            'labels': {
                'type': 'object',
                'description': 'Additional labels for the alert',
                'additionalProperties': {'type': 'string'}
            },
            'annotations': {
                'type': 'object',
                'description': 'Additional annotations for the alert',
                'additionalProperties': {'type': 'string'}
            }
        },
        'required': ['name', 'expr']
    }
)
async def add_alert_rule(
    name: str,
    expr: str,
    for_duration: str = '5m',
    severity: str = 'warning',
    summary: Optional[str] = None,
    description: Optional[str] = None,
    labels: Optional[Dict[str, str]] = None,
    annotations: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
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
            return {
                "status": "error",
                "error": "Failed to create alert rules directory"
            }
        
        # Prepare the alert rule
        alert_rule = {
            'alert': name,
            'expr': expr,
            'for': for_duration,
            'labels': {
                'severity': severity,
                **(labels or {})
            },
            'annotations': {}
        }
        
        if summary:
            alert_rule['annotations']['summary'] = summary
        if description:
            alert_rule['annotations']['description'] = description
        if annotations:
            alert_rule['annotations'].update(annotations)
        
        # Load existing rules or create new
        rules = {'groups': [{'name': 'docker-mcp', 'rules': []}]}
        if alert_rules_dir.exists():
            with open(alert_rules_dir, 'r') as f:
                try:
                    rules = yaml.safe_load(f) or rules
                except yaml.YAMLError as e:
                    logger.error(f"Error parsing alert rules: {e}")
        
        # Add the new rule
        if 'groups' not in rules or not rules['groups']:
            rules['groups'] = [{'name': 'docker-mcp', 'rules': []}]
        
        # Check if rule with same name exists
        for group in rules['groups']:
            if 'rules' in group:
                group['rules'] = [r for r in group['rules'] if r.get('alert') != name]
        
        # Add to first group or create a new one
        if not rules['groups']:
            rules['groups'].append({'name': 'docker-mcp', 'rules': []})
        
        rules['groups'][0].setdefault('rules', []).append(alert_rule)
        
        # Save back to file
        with open(alert_rules_dir, 'w') as f:
            yaml.dump(rules, f, default_flow_style=False)
        
        # Reload Prometheus configuration
        # This would typically be done via a separate API call or SIGHUP
        
        return {
            "status": "success",
            "message": "Alert rule added",
            "alert": alert_rule
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to add alert rule: {str(e)}"
        }

@Tool(
    name="remove_alert_rule",
    description="Remove an alert rule by name",
    parameters={
        'type': 'object',
        'properties': {
            'name': {
                'type': 'string',
                'description': 'Name of the alert rule to remove'
            }
        },
        'required': ['name']
    }
)
async def remove_alert_rule(name: str) -> Dict[str, Any]:
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
            return {
                "status": "error",
                "error": "No alert rules configured"
            }
        
        # Load existing rules
        with open(alert_rules_dir, 'r') as f:
            rules = yaml.safe_load(f) or {}
        
        # Remove the rule
        removed = False
        for group in rules.get('groups', []):
            if 'rules' in group:
                original_count = len(group['rules'])
                group['rules'] = [r for r in group['rules'] if r.get('alert') != name]
                if len(group['rules']) < original_count:
                    removed = True
        
        if not removed:
            return {
                "status": "error",
                "error": f"Alert rule '{name}' not found"
            }
        
        # Save back to file
        with open(alert_rules_dir, 'w') as f:
            yaml.dump(rules, f, default_flow_style=False)
        
        # Reload Prometheus configuration
        # This would typically be done via a separate API call or SIGHUP
        
        return {
            "status": "success",
            "message": "Alert rule removed",
            "removed_alert": name
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to remove alert rule: {str(e)}"
        }
