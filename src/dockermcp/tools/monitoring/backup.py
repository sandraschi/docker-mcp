"""
Backup and Restore Tools for Monitoring Stack

This module provides tools to backup and restore the monitoring stack's data.
"""
import shutil
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from dockermcp.logging_config import logger
from dockermcp.mcp_instance import mcp

# Default backup directory
DEFAULT_BACKUP_DIR = Path("/var/backups/dockermcp/monitoring")

class MonitoringBackup:
    """Handles backup and restore of monitoring stack data."""

    def __init__(self, backup_dir: str | Path | None = None):
        """Initialize the backup manager."""
        self.backup_dir = Path(backup_dir) if backup_dir else DEFAULT_BACKUP_DIR
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def _create_backup_name(self, prefix: str = "backup") -> str:
        """Generate a backup filename with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.tar.gz"

    def _get_data_paths(self) -> list[Path]:
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

    def create_backup(self, output_file: str | Path | None = None) -> dict[str, Any]:
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
                "error": f"Failed to create backup: {e!s}"
            }

    def restore_backup(self, backup_file: str | Path, target_dir: str | Path = "/") -> dict[str, Any]:
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
                    tar.extractall(tmp_dir, filter='data')

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
                "error": f"Failed to restore backup: {e!s}"
            }

    def list_backups(self) -> dict[str, Any]:
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
                "error": f"Failed to list backups: {e!s}"
            }

# Pydantic Models for Parameters
class CreateBackupParams(BaseModel):
    """Parameters for creating a monitoring backup."""
    output_file: str | None = Field(
        None,
        description="Path to save the backup file (optional)"
    )
    backup_dir: str | None = Field(
        None,
        description="Directory to save the backup (if output_file not specified)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "output_file": "/path/to/backup.tar.gz",
                "backup_dir": "/var/backups/dockermcp/monitoring"
            }
        }
    )

class RestoreBackupParams(BaseModel):
    """Parameters for restoring a monitoring backup."""
    backup_file: str = Field(..., description="Path to the backup file to restore")
    target_dir: str = Field(
        "/",
        description="Target directory to restore to (default: /)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "backup_file": "/var/backups/dockermcp/monitoring/backup_20230912_123456.tar.gz",
                "target_dir": "/"
            }
        }
    )

class ListBackupsParams(BaseModel):
    """Parameters for listing monitoring backups."""
    backup_dir: str | None = Field(
        None,
        description="Directory containing the backups (optional)"
    )

# Create a default instance
backup_manager = MonitoringBackup()

@mcp.tool
async def create_monitoring_backup(params: CreateBackupParams) -> dict[str, Any]:
    """
    Create a backup of the monitoring stack's data.

    Args:
        params: CreateBackupParams containing backup configuration

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
        manager = MonitoringBackup(params.backup_dir) if params.backup_dir else backup_manager
        return manager.create_backup(params.output_file)
    except Exception as e:
        error_msg = f"Failed to create backup: {e!s}"
        logger.error(error_msg, exc_info=True)
        return {
            "status": "error",
            "error": error_msg
        }

@mcp.tool
async def restore_monitoring_backup(params: RestoreBackupParams) -> dict[str, Any]:
    """
    Restore the monitoring stack's data from a backup.

    Args:
        params: RestoreBackupParams containing restore configuration

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
        return backup_manager.restore_backup(params.backup_file, params.target_dir)
    except Exception as e:
        error_msg = f"Failed to restore backup: {e!s}"
        logger.error(error_msg, exc_info=True)
        return {
            "status": "error",
            "error": error_msg
        }

@mcp.tool
async def list_monitoring_backups(params: ListBackupsParams) -> dict[str, Any]:
    """
    List available monitoring backups.

    Args:
        params: ListBackupsParams containing backup directory

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
        manager = MonitoringBackup(params.backup_dir) if params.backup_dir else backup_manager
        return manager.list_backups()
    except Exception as e:
        error_msg = f"Failed to list backups: {e!s}"
        logger.error(error_msg, exc_info=True)
        return {
            "status": "error",
            "error": error_msg
        }
