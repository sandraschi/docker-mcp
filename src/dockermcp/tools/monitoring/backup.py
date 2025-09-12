"""
Backup and Restore Tools for Monitoring Stack

This module provides tools to backup and restore the monitoring stack's data.
"""
import json
import shutil
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, BinaryIO, Union

from fastmcp.tools import Tool
from dockermcp.logging_config import logger

# Default backup directory
DEFAULT_BACKUP_DIR = Path("/var/backups/dockermcp/monitoring")

class MonitoringBackup:
    """Handles backup and restore of monitoring stack data."""
    
    def __init__(self, backup_dir: Union[str, Path] = None):
        """Initialize the backup manager."""
        self.backup_dir = Path(backup_dir) if backup_dir else DEFAULT_BACKUP_DIR
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def _create_backup_name(self, prefix: str = "backup") -> str:
        """Generate a backup filename with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.tar.gz"
    
    def _get_data_paths(self) -> List[Path]:
        """Get paths to backup."""
        return [
            # Grafana data
            Path("/var/lib/grafana"),
            # Prometheus data
            Path("/prometheus"),
            # Loki data
            Path("/loki"),
            # Alert rules
            Path("/etc/prometheus/alert.rules"),
            # Grafana dashboards
            Path("/etc/grafana/provisioning/dashboards"),
            # Alertmanager config
            Path("/etc/alertmanager/alertmanager.yml"),
        ]
    
    def create_backup(self, output_file: Union[str, Path] = None) -> Dict[str, Any]:
        """Create a backup of monitoring data."""
        try:
            if not output_file:
                output_file = self.backup_dir / self._create_backup_name()
            else:
                output_file = Path(output_file)
            
            # Ensure output directory exists
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Get paths to back up
            paths = self._get_data_paths()
            
            # Create tar.gz archive
            with tarfile.open(output_file, "w:gz") as tar:
                for path in paths:
                    if path.exists():
                        tar.add(path, arcname=path.name)
            
            return {
                "status": "success",
                "message": "Backup created successfully",
                "backup_file": str(output_file),
                "size_mb": output_file.stat().st_size / (1024 * 1024)
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to create backup: {str(e)}"
            }
    
    def restore_backup(self, backup_file: Union[str, Path], target_dir: Union[str, Path] = "/") -> Dict[str, Any]:
        """Restore monitoring data from a backup."""
        try:
            backup_file = Path(backup_file)
            target_dir = Path(target_dir)
            
            if not backup_file.exists():
                return {
                    "status": "error",
                    "error": f"Backup file not found: {backup_file}"
                }
            
            # Extract the backup
            with tarfile.open(backup_file, "r:gz") as tar:
                # Extract to a temporary directory first
                with tempfile.TemporaryDirectory() as tmp_dir:
                    tar.extractall(tmp_dir)
                    
                    # Move files to target directory
                    for item in Path(tmp_dir).iterdir():
                        dest = target_dir / item.name
                        if dest.exists():
                            if dest.is_dir():
                                shutil.rmtree(dest)
                            else:
                                dest.unlink()
                        shutil.move(str(item), str(dest))
            
            return {
                "status": "success",
                "message": "Backup restored successfully",
                "backup_file": str(backup_file),
                "target_dir": str(target_dir)
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to restore backup: {str(e)}"
            }
    
    def list_backups(self) -> Dict[str, Any]:
        """List available backups."""
        try:
            if not self.backup_dir.exists():
                return {
                    "status": "success",
                    "backups": [],
                    "backup_dir": str(self.backup_dir)
                }
            
            backups = []
            for file in sorted(self.backup_dir.glob("*.tar.gz"), key=lambda f: f.stat().st_mtime, reverse=True):
                backups.append({
                    "name": file.name,
                    "path": str(file),
                    "size_mb": file.stat().st_size / (1024 * 1024),
                    "modified": datetime.fromtimestamp(file.stat().st_mtime).isoformat()
                })
            
            return {
                "status": "success",
                "backups": backups,
                "backup_dir": str(self.backup_dir)
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to list backups: {str(e)}"
            }

# Create a default instance
backup_manager = MonitoringBackup()

@Tool(
    name="create_monitoring_backup",
    description="Create a backup of the monitoring stack's data",
    parameters={
        'type': 'object',
        'properties': {
            'output_file': {
                'type': 'string',
                'description': 'Path to save the backup file (optional)'
            },
            'backup_dir': {
                'type': 'string',
                'description': 'Directory to save the backup (if output_file not specified)'
            }
        }
    }
)
async def create_monitoring_backup(
    output_file: str = None,
    backup_dir: str = None
) -> Dict[str, Any]:
    """
    Create a backup of the monitoring stack's data.
    
    Args:
        output_file: Path to save the backup file (optional)
        backup_dir: Directory to save the backup (if output_file not specified)
        
    Returns:
        Dictionary with the result of the operation
        
    Example:
        >>> await create_monitoring_backup()
        {
            'status': 'success',
            'message': 'Backup created successfully',
            'backup_file': '/var/backups/dockermcp/monitoring/backup_20230912_123456.tar.gz',
            'size_mb': 42.5
        }
    """
    try:
        manager = MonitoringBackup(backup_dir) if backup_dir else backup_manager
        return manager.create_backup(output_file)
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to create backup: {str(e)}"
        }

@Tool(
    name="restore_monitoring_backup",
    description="Restore the monitoring stack's data from a backup",
    parameters={
        'type': 'object',
        'properties': {
            'backup_file': {
                'type': 'string',
                'description': 'Path to the backup file to restore'
            },
            'target_dir': {
                'type': 'string',
                'default': '/',
                'description': 'Target directory to restore to (default: /)'
            }
        },
        'required': ['backup_file']
    }
)
async def restore_monitoring_backup(
    backup_file: str,
    target_dir: str = "/"
) -> Dict[str, Any]:
    """
    Restore the monitoring stack's data from a backup.
    
    Args:
        backup_file: Path to the backup file to restore
        target_dir: Target directory to restore to (default: /)
        
    Returns:
        Dictionary with the result of the operation
        
    Example:
        >>> await restore_monitoring_backup(
        ...     backup_file="/var/backups/dockermcp/monitoring/backup_20230912_123456.tar.gz"
        ... )
        {
            'status': 'success',
            'message': 'Backup restored successfully',
            'backup_file': '/var/backups/dockermcp/monitoring/backup_20230912_123456.tar.gz',
            'target_dir': '/'
        }
    """
    try:
        return backup_manager.restore_backup(backup_file, target_dir)
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to restore backup: {str(e)}"
        }

@Tool(
    name="list_monitoring_backups",
    description="List available monitoring backups",
    parameters={
        'type': 'object',
        'properties': {
            'backup_dir': {
                'type': 'string',
                'description': 'Directory containing the backups (optional)'
            }
        }
    }
)
async def list_monitoring_backups(backup_dir: str = None) -> Dict[str, Any]:
    """
    List available monitoring backups.
    
    Args:
        backup_dir: Directory containing the backups (optional)
        
    Returns:
        Dictionary with the list of available backups
        
    Example:
        >>> await list_monitoring_backups()
        {
            'status': 'success',
            'backups': [
                {
                    'name': 'backup_20230912_123456.tar.gz',
                    'path': '/var/backups/dockermcp/monitoring/backup_20230912_123456.tar.gz',
                    'size_mb': 42.5,
                    'modified': '2023-09-12T12:34:56'
                }
            ],
            'backup_dir': '/var/backups/dockermcp/monitoring'
        }
    """
    try:
        manager = MonitoringBackup(backup_dir) if backup_dir else backup_manager
        return manager.list_backups()
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to list backups: {str(e)}"
        }
