#!/usr/bin/env python3
"""
DockerMCP Monitoring Stack Manager

This script provides commands to manage the monitoring stack (Prometheus, Grafana, Loki, etc.).
"""
import os
import sys
import subprocess
import time
import webbrowser
from pathlib import Path
from typing import Optional, List, Dict, Any

import click
import yaml
from docker import from_env
from docker.errors import DockerException

# Constants
MONITORING_DIR = Path(__file__).parent.absolute()
DOCKER_COMPOSE_FILE = MONITORING_DIR / "docker-compose-monitoring.yml"
ENV_FILE = MONITORING_DIR / ".env"

# Docker client
try:
    docker_client = from_env()
except DockerException as e:
    print(f"Error initializing Docker client: {e}")
    docker_client = None

class MonitoringManager:
    """Manages the monitoring stack."""
    
    def __init__(self):
        self.compose_cmd = ["docker-compose", "-f", str(DOCKER_COMPOSE_FILE)]
        
        # Load environment variables if .env exists
        self.env = {}
        if ENV_FILE.exists():
            with open(ENV_FILE) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        self.env[key] = value.strip('\'"')
    
    def run_command(self, cmd: List[str], **kwargs) -> int:
        """Run a shell command and return the exit code."""
        try:
            process = subprocess.run(
                cmd,
                cwd=MONITORING_DIR,
                check=False,
                **kwargs
            )
            return process.returncode
        except Exception as e:
            print(f"Error running command: {' '.join(cmd)}")
            print(f"Error: {e}")
            return 1
    
    def start(self, build: bool = False) -> int:
        """Start the monitoring stack."""
        cmd = self.compose_cmd + ["up", "-d"]
        if build:
            cmd.append("--build")
        return self.run_command(cmd)
    
    def stop(self) -> int:
        """Stop the monitoring stack."""
        return self.run_command(self.compose_cmd + ["down"])
    
    def restart(self) -> int:
        """Restart the monitoring stack."""
        self.stop()
        return self.start()
    
    def status(self) -> int:
        """Show the status of monitoring services."""
        return self.run_command(self.compose_cmd + ["ps"])
    
    def logs(self, follow: bool = False, tail: int = 100) -> int:
        """Show logs from monitoring services."""
        cmd = self.compose_cmd + ["logs", f"--tail={tail}"]
        if follow:
            cmd.append("-f")
        return self.run_command(cmd)
    
    def open_grafana(self) -> None:
        """Open Grafana in the default web browser."""
        url = "http://localhost:3000"
        print(f"Opening Grafana at {url}")
        webbrowser.open(url)
    
    def open_prometheus(self) -> None:
        """Open Prometheus in the default web browser."""
        url = "http://localhost:9090"
        print(f"Opening Prometheus at {url}")
        webbrowser.open(url)
    
    def open_loki(self) -> None:
        """Open Loki in the default web browser."""
        url = "http://localhost:3100"
        print(f"Opening Loki at {url}")
        webbrowser.open(url)
    
    def check_requirements(self) -> bool:
        """Check if all required tools are installed."""
        required_commands = ["docker", "docker-compose"]
        missing = []
        
        for cmd in required_commands:
            try:
                subprocess.run(
                    [cmd, "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True
                )
            except (subprocess.SubprocessError, FileNotFoundError):
                missing.append(cmd)
        
        if missing:
            print("The following required tools are missing:")
            for cmd in missing:
                print(f"- {cmd}")
            print("\nPlease install them before continuing.")
            return False
        return True

@click.group()
@click.pass_context
def cli(ctx):
    """DockerMCP Monitoring Stack Manager."""
    ctx.ensure_object(dict)
    ctx.obj['manager'] = MonitoringManager()

@cli.command()
def start():
    """Start the monitoring stack."""
    manager = MonitoringManager()
    if not manager.check_requirements():
        sys.exit(1)
    sys.exit(manager.start())

@cli.command()
def stop():
    """Stop the monitoring stack."""
    manager = MonitoringManager()
    sys.exit(manager.stop())

@cli.command()
def restart():
    """Restart the monitoring stack."""
    manager = MonitoringManager()
    sys.exit(manager.restart())

@cli.command()
def status():
    """Show the status of monitoring services."""
    manager = MonitoringManager()
    sys.exit(manager.status())

@cli.command()
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
@click.option('--tail', type=int, default=100, help='Number of lines to show from the end of the logs')
def logs(follow, tail):
    """Show logs from monitoring services."""
    manager = MonitoringManager()
    sys.exit(manager.logs(follow=follow, tail=tail))

@cli.command()
def grafana():
    """Open Grafana in the default web browser."""
    manager = MonitoringManager()
    manager.open_grafana()

@cli.command()
def prometheus():
    """Open Prometheus in the default web browser."""
    manager = MonitoringManager()
    manager.open_prometheus()

@cli.command()
def loki():
    """Open Loki in the default web browser."""
    manager = MonitoringManager()
    manager.open_loki()

@cli.command()
@click.option('--admin-user', default='admin', help='Grafana admin username')
@click.option('--admin-password', default='admin', help='Grafana admin password')
@click.option('--port', default=3000, help='Grafana port')
@click.option('--prometheus-port', default=9090, help='Prometheus port')
@click.option('--loki-port', default=3100, help='Loki port')
@click.option('--force', is_flag=True, help='Overwrite existing .env file')
def setup(admin_user, admin_password, port, prometheus_port, loki_port, force):
    """Generate configuration files for the monitoring stack."""
    # Create directories if they don't exist
    (MONITORING_DIR / "prometheus").mkdir(exist_ok=True)
    (MONITORING_DIR / "grafana").mkdir(exist_ok=True)
    (MONITORING_DIR / "loki").mkdir(exist_ok=True)
    (MONITORING_DIR / "promtail").mkdir(exist_ok=True)
    
    # Create .env file if it doesn't exist or if force is True
    if not ENV_FILE.exists() or force:
        with open(ENV_FILE, 'w') as f:
            f.write(f"# DockerMCP Monitoring Stack Configuration\n")
            f.write(f"GRAFANA_ADMIN_USER={admin_user}\n")
            f.write(f"GRAFANA_ADMIN_PASSWORD={admin_password}\n")
            f.write(f"GRAFANA_PORT={port}\n")
            f.write(f"PROMETHEUS_PORT={prometheus_port}\n")
            f.write(f"LOKI_PORT={loki_port}\n")
        print(f"Created {ENV_FILE}")
    else:
        print(f"{ENV_FILE} already exists. Use --force to overwrite.")
    
    print("\nSetup complete. You can now start the monitoring stack with:")
    print("  python manage_monitoring.py start")
    print("\nAccess the services at:")
    print(f"  Grafana:     http://localhost:{port}")
    print(f"  Prometheus:  http://localhost:{prometheus_port}")
    print(f"  Loki:        http://localhost:{loki_port}")

if __name__ == "__main__":
    cli()
