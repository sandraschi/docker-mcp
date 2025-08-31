"""
Process and subprocess utilities for Docker MCP.

This module provides utilities for running subprocesses with proper error handling,
output capture, and JSON processing.
"""
import os
import re
import json
import signal
import logging
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Union, List, Tuple, TypeVar, Type, Callable

from .json_utils import safe_json_loads, safe_json_dumps, JSONValidationError

logger = logging.getLogger(__name__)

# Type variable for command output
try:
    from typing import Literal
    OutputType = Literal['text', 'json', 'lines']
except ImportError:
    OutputType = str  # Fallback for Python <3.8

class ProcessError(subprocess.SubprocessError):
    """Custom exception for process-related errors."""
    def __init__(self, message: str, cmd: List[str], returncode: int = None,
                 stdout: str = None, stderr: str = None):
        super().__init__(returncode, cmd, stdout, stderr)
        self.message = message
        self.cmd = cmd
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self) -> str:
        return f"{self.message}\nCommand: {' '.join(self.cmd)}\nExit code: {self.returncode}" + \
               (f"\nStdout: {self.stdout}" if self.stdout else "") + \
               (f"\nStderr: {self.stderr}" if self.stderr else "")

def run_command(
    cmd: Union[str, List[str]],
    capture_output: bool = True,
    check: bool = True,
    output_type: OutputType = 'text',
    cwd: Optional[Union[str, Path]] = None,
    env: Optional[Dict[str, str]] = None,
    timeout: Optional[float] = None,
    **kwargs
) -> Union[str, Dict, List, Tuple[int, str, str]]:
    """
    Run a command with improved error handling and output processing.
    
    Args:
        cmd: Command to run as a string or list of strings
        capture_output: Whether to capture stdout/stderr
        check: Whether to raise an exception on non-zero exit code
        output_type: Type of output processing: 'text', 'json', or 'lines'
        cwd: Working directory for the command
        env: Environment variables to set for the command
        timeout: Timeout in seconds
        **kwargs: Additional arguments to subprocess.run()
        
    Returns:
        If output_type='json', returns parsed JSON (dict or list)
        If output_type='lines', returns list of lines
        If capture_output=True, returns the stdout as string
        Otherwise, returns a tuple of (returncode, stdout, stderr)
        
    Raises:
        ProcessError: If check=True and command fails or output is invalid
        subprocess.TimeoutExpired: If command times out
    """
    # Convert command to list if it's a string
    if isinstance(cmd, str):
        cmd = [cmd] if ' ' not in cmd else cmd.split()
    
    # Ensure we're capturing output for non-text output types
    if output_type in ('json', 'lines') and not capture_output:
        capture_output = True
    
    # Prepare environment
    env = env or os.environ.copy()
    
    # Log the command being run
    logger.debug(f"Running command: {' '.join(cmd)}")
    if cwd:
        logger.debug(f"Working directory: {cwd}")
    
    try:
        # Run the command with a timeout
        result = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            env=env,
            capture_output=capture_output,
            text=True,
            timeout=timeout,
            **kwargs
        )
        
        # Log any stderr output
        if result.stderr and result.stderr.strip():
            logger.warning(f"Command stderr: {result.stderr.strip()}")
        
        # Check return code if requested
        if check and result.returncode != 0:
            raise ProcessError(
                f"Command returned non-zero exit status {result.returncode}",
                cmd=cmd,
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr
            )
        
        # Return appropriate output based on capture_output and output_type
        if not capture_output:
            return result.returncode, "", ""
        
        if output_type == 'json':
            try:
                return safe_json_loads(
                    result.stdout,
                    default={},
                    context=f"command output from {' '.join(cmd)}",
                    strict=check
                )
            except JSONValidationError as e:
                logger.error(f"Invalid JSON output: {e}")
                if check:
                    raise ProcessError(
                        f"Invalid JSON output: {e}",
                        cmd=cmd,
                        returncode=result.returncode,
                        stdout=result.stdout,
                        stderr=result.stderr
                    )
                return {}
        
        elif output_type == 'lines':
            return [line for line in result.stdout.splitlines() if line.strip()]
        
        return result.stdout.strip()
    
    except subprocess.TimeoutExpired as e:
        logger.error(f"Command timed out after {e.timeout} seconds: {' '.join(cmd)}")
        raise
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}: {e}")
        if check:
            raise ProcessError(
                f"Command failed with exit code {e.returncode}",
                cmd=cmd,
                returncode=e.returncode,
                stdout=e.stdout,
                stderr=e.stderr
            ) from e
        return e.returncode, e.stdout or "", e.stderr or ""
    except Exception as e:
        logger.error(f"Unexpected error running command: {e}", exc_info=True)
        if check:
            raise ProcessError(
                f"Unexpected error: {str(e)}",
                cmd=cmd,
                returncode=getattr(e, 'returncode', -1)
            ) from e
        raise

def run_docker_command(
    subcommand: str,
    args: Optional[List[str]] = None,
    output_type: Optional[OutputType] = 'json',
    docker_host: Optional[str] = None,
    **kwargs
) -> Union[str, Dict, List, bytes]:
    """
    Run a docker command with improved error handling and output processing.
    
    Args:
        subcommand: Docker subcommand (e.g., 'ps', 'images', 'inspect')
        args: Additional arguments for the docker command
        output_type: Type of output processing: 'text', 'json', 'lines', or None for raw bytes
        docker_host: Docker daemon socket or host to connect to
        **kwargs: Additional arguments to run_command()
        
    Returns:
        Processed command output based on output_type
        
    Raises:
        ProcessError: If command fails or output is invalid
    """
    if args is None:
        args = []
    
    # Build the base command
    cmd = ['docker']
    
    # Add Docker host if specified
    if docker_host:
        cmd.extend(['-H', docker_host])
    
    # Add subcommand and arguments
    cmd.append(subcommand)
    cmd.extend(args)
    
    # Configure JSON output for commands that support it
    if output_type == 'json' and '--format' not in args and subcommand in [
        'ps', 'images', 'volume', 'network', 'system', 'container', 'image', 'node', 'secret', 'service'
    ]:
        cmd.extend(['--format', '{{json .}}'])
    
    # Set default timeout if not specified
    if 'timeout' not in kwargs:
        kwargs['timeout'] = 300  # 5 minute default timeout for Docker commands
    
    try:
        # Run the command with the appropriate output type
        result = run_command(
            cmd,
            output_type=output_type,
            check=True,
            **kwargs
        )
        
        # Handle empty results for common list commands
        if not result and output_type == 'json':
            if subcommand in ['ps', 'images', 'volume', 'network', 'container', 'image']:
                return []
            return {}
            
        return result
        
    except ProcessError as e:
        # Add more context to the error message
        if "permission denied" in str(e).lower():
            e.message = "Permission denied when trying to connect to Docker daemon. " \
                       "Make sure the Docker daemon is running and you have the necessary permissions."
        raise e from None
    except Exception as e:
        logger.error(f"Unexpected error running docker command: {e}", exc_info=True)
        raise ProcessError(
            f"Failed to execute docker {subcommand}: {str(e)}",
            cmd=cmd
        ) from e
