"""
Container filesystem operations for Docker MCP.

This module provides tools for interacting with container filesystems, including
listing directories, reading files, uploading/downloading files, and managing
permissions. It follows FastMCP 2.12+ standards for tool registration and error handling.
"""
from __future__ import annotations

import base64
import os
import stat
import tarfile
import tempfile
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional, Union, AsyncGenerator, BinaryIO

import docker
from docker.errors import DockerException, APIError, NotFound, ContainerError
from fastmcp.tools.tool import Tool
from pydantic import BaseModel, Field, ConfigDict

from dockermcp.logging_config import logger

class FileInfo(BaseModel):
    """Information about a file or directory in a container."""
    name: str = Field(..., description="Name of the file or directory")
    path: str = Field(..., description="Full path in the container")
    type: str = Field(..., description="Type (file, directory, symlink, etc.)")
    size: int = Field(..., description="Size in bytes")
    mode: int = Field(..., description="File mode/permissions")
    mtime: str = Field(..., description="Last modification time (ISO 8601)")
    uid: int = Field(..., description="Owner user ID")
    gid: int = Field(..., description="Owner group ID")
    user: str = Field(..., description="Owner username (if available)")
    group: str = Field(..., description="Owner group name (if available)")

class FileContent(BaseModel):
    """File content and metadata."""
    path: str = Field(..., description="File path in the container")
    content: str = Field(..., description="File content as base64-encoded string")
    encoding: str = Field(..., description="Content encoding (e.g., 'base64')")
    size: int = Field(..., description="Size of the content in bytes")
    truncated: bool = Field(..., description="Whether the content was truncated")

@Tool(
    name="list_container_directory",
    description="List contents of a directory in a container",
    parameters={
        'type': 'object',
        'properties': {
            'container_id': {
                'type': 'string',
                'description': 'ID or name of the container'
            },
            'path': {
                'type': 'string',
                'default': '/',
                'description': 'Path to list (default: /)'
            },
            'recursive': {
                'type': 'boolean',
                'default': False,
                'description': 'List contents recursively'
            },
            'include_hidden': {
                'type': 'boolean',
                'default': False,
                'description': 'Include hidden files (starting with .)'
            },
            'max_depth': {
                'type': 'integer',
                'minimum': 1,
                'default': 10,
                'description': 'Maximum depth for recursive listing'
            }
        },
        'required': ['container_id']
    }
)
async def list_container_directory(
    container_id: str,
    path: str = '/',
    recursive: bool = False,
    include_hidden: bool = False,
    max_depth: int = 10
) -> Dict[str, Any]:
    """
    List contents of a directory in a container.
    
    This function provides a way to explore the filesystem of a running container,
    similar to the 'ls' command. It can list directory contents with detailed
    file information including permissions, ownership, size, and modification time.
    
    Args:
        container_id: ID or name of the container
        path: Directory path to list (default: /)
        recursive: List contents recursively
        include_hidden: Include hidden files (starting with .)
        max_depth: Maximum depth for recursive listing
        
    Returns:
        Dictionary with directory contents and metadata
        
    Example:
        >>> await list_container_directory(
        ...     container_id="my-container",
        ...     path="/app",
        ...     recursive=True,
        ...     max_depth=2
        ... )
        {
            "status": "success",
            "container_id": "a1b2c3d4e5f6",
            "path": "/app",
            "exists": True,
            "is_directory": True,
            "contents": [
                {
                    "name": "app.py",
                    "path": "/app/app.py",
                    "type": "file",
                    "size": 1024,
                    "mode": 0o644,
                    "mtime": "2023-01-01T12:00:00Z",
                    "uid": 1000,
                    "gid": 1000,
                    "user": "appuser",
                    "group": "appgroup"
                },
                {
                    "name": "config",
                    "path": "/app/config",
                    "type": "directory",
                    "size": 4096,
                    "mode": 0o755,
                    "mtime": "2023-01-01T12:00:00Z",
                    "uid": 1000,
                    "gid": 1000,
                    "user": "appuser",
                    "group": "appgroup"
                }
            ]
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        try:
            container = client.containers.get(container_id)
        except NotFound:
            return {
                "status": "error",
                "container_id": container_id,
                "error": f"Container not found: {container_id}"
            }
        
        # Normalize path
        path = os.path.normpath(path).replace('\\', '/')
        if not path.startswith('/'):
            path = '/' + path
        
        # Execute 'ls' command to get directory listing
        cmd = ['ls', '-la', '--time-style=+%s', path]
        if recursive:
            cmd.insert(1, '-R')
            cmd.insert(1, f'--max-depth={max_depth}')
        
        try:
            # Execute the command
            exec_result = container.exec_run(
                cmd,
                demux=True,
                tty=False
            )
            
            # Check for errors
            if exec_result.exit_code != 0:
                error_output = exec_result.output[1] or b''
                return {
                    "status": "error",
                    "container_id": container_id,
                    "path": path,
                    "error": f"Failed to list directory: {error_output.decode('utf-8', errors='replace').strip()}"
                }
            
            # Parse the output
            output = exec_result.output[0].decode('utf-8', errors='replace')
            entries = _parse_ls_output(output, path, recursive)
            
            # Filter out hidden files if needed
            if not include_hidden:
                entries = [e for e in entries if not os.path.basename(e['name']).startswith('.')]
            
            return {
                "status": "success",
                "container_id": container_id,
                "path": path,
                "exists": True,
                "is_directory": True,
                "contents": entries
            }
            
        except ContainerError as e:
            if 'No such file or directory' in str(e):
                return {
                    "status": "success",
                    "container_id": container_id,
                    "path": path,
                    "exists": False,
                    "is_directory": False,
                    "contents": []
                }
            raise
            
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": error_msg}
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": "Docker daemon not available"}
        
    except Exception as e:
        error_msg = f"Unexpected error listing container directory: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}

def _parse_ls_output(ls_output: str, base_path: str, recursive: bool) -> List[Dict[str, Any]]:
    """
    Parse the output of 'ls -la' command into structured data.
    
    Args:
        ls_output: Raw output from 'ls -la' command
        base_path: Base path that was listed
        recursive: Whether the listing is recursive
        
    Returns:
        List of file/directory entries with metadata
    """
    entries = []
    current_dir = base_path
    
    for line in ls_output.splitlines():
        line = line.strip()
        if not line or line.endswith(':'):
            # Directory header in recursive mode
            if recursive and line.endswith(':'):
                current_dir = line[:-1].strip()
            continue
            
        # Skip the 'total X' line
        if line.startswith('total '):
            continue
            
        try:
            # Parse the ls -l output
            parts = line.split()
            if len(parts) < 8:
                continue
                
            # Extract file mode, links, owner, group, size, date, and name
            mode_str = parts[0]
            links = int(parts[1])
            owner = parts[2]
            group = parts[3]
            size = int(parts[4])
            mtime_epoch = int(parts[7])
            name = ' '.join(parts[8:])
            
            # Skip . and .. entries
            if name in ('.', '..'):
                continue
                
            # Determine file type
            if mode_str.startswith('d'):
                file_type = 'directory'
            elif mode_str.startswith('l'):
                file_type = 'symlink'
                # Handle symlink target (name -> target)
                if ' -> ' in name:
                    name, _ = name.split(' -> ', 1)
            else:
                file_type = 'file'
            
            # Convert mode string to octal
            mode = 0
            for i, c in enumerate(mode_str[1:10]):
                if c != '-':
                    mode |= (0o100 >> (i // 3)) << (8 - i)
            
            # Build full path
            if name.startswith('/'):
                full_path = name
            else:
                full_path = os.path.join(current_dir, name).replace('\\', '/')
            
            # Add the entry
            entries.append({
                'name': name,
                'path': full_path,
                'type': file_type,
                'size': size,
                'mode': mode,
                'mtime': datetime.fromtimestamp(mtime_epoch, tz=datetime.timezone.utc).isoformat(),
                'uid': 0,  # These would require additional lookups
                'gid': 0,
                'user': owner,
                'group': group,
                'links': links
            })
            
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse ls output line: {line}")
            continue
    
    return entries

@Tool(
    name="read_container_file",
    description="Read the contents of a file from a container",
    parameters={
        'type': 'object',
        'properties': {
            'container_id': {
                'type': 'string',
                'description': 'ID or name of the container'
            },
            'path': {
                'type': 'string',
                'description': 'Path to the file in the container'
            },
            'offset': {
                'type': 'integer',
                'minimum': 0,
                'default': 0,
                'description': 'Byte offset to start reading from'
            },
            'length': {
                'type': 'integer',
                'minimum': 1,
                'maximum': 10485760,  # 10MB max
                'default': 65536,     # 64KB default
                'description': 'Maximum number of bytes to read (max 10MB)'
            },
            'encoding': {
                'type': 'string',
                'enum': ['base64', 'utf-8', 'latin-1'],
                'default': 'base64',
                'description': 'Encoding for the file content'
            }
        },
        'required': ['container_id', 'path']
    }
)
async def read_container_file(
    container_id: str,
    path: str,
    offset: int = 0,
    length: int = 65536,
    encoding: str = 'base64'
) -> Dict[str, Any]:
    """
    Read the contents of a file from a container.
    
    This function allows reading file contents from a container's filesystem
    with support for partial reads and different encodings. For large files,
    it's recommended to read in chunks using the offset and length parameters.
    
    Args:
        container_id: ID or name of the container
        path: Path to the file in the container
        offset: Byte offset to start reading from
        length: Maximum number of bytes to read (max 10MB)
        encoding: Encoding for the file content (base64, utf-8, or latin-1)
        
    Returns:
        Dictionary with file content and metadata
        
    Example:
        >>> await read_container_file(
        ...     container_id="my-container",
        ...     path="/app/config.json",
        ...     length=1024
        ... )
        {
            "status": "success",
            "container_id": "a1b2c3d4e5f6",
            "path": "/app/config.json",
            "exists": True,
            "is_file": True,
            "size": 512,
            "content": "eyJkYiI6IHs...",
            "encoding": "base64",
            "truncated": False
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        try:
            container = client.containers.get(container_id)
        except NotFound:
            return {
                "status": "error",
                "container_id": container_id,
                "error": f"Container not found: {container_id}"
            }
        
        # Normalize path
        path = os.path.normpath(path).replace('\\', '/')
        
        try:
            # Get file info first to check if it exists and is a file
            stat_result = container.exec_run(
                ['stat', '-c', '%F %s %Y %f %u %g', path],
                demux=True
            )
            
            if stat_result.exit_code != 0:
                return {
                    "status": "success",
                    "container_id": container_id,
                    "path": path,
                    "exists": False,
                    "is_file": False,
                    "error": "File not found or not accessible"
                }
            
            # Parse stat output
            stat_parts = stat_result.output[0].decode('utf-8').strip().split()
            if len(stat_parts) < 6:
                return {
                    "status": "error",
                    "container_id": container_id,
                    "path": path,
                    "error": "Failed to parse file information"
                }
            
            file_type = stat_parts[0]
            file_size = int(stat_parts[1])
            mtime = int(stat_parts[2])
            mode = int(stat_parts[3], 16)  # Convert hex to int
            uid = int(stat_parts[4])
            gid = int(stat_parts[5])
            
            if not file_type.startswith('regular file'):
                return {
                    "status": "error",
                    "container_id": container_id,
                    "path": path,
                    "error": "Not a regular file"
                }
            
            # Check if offset is beyond file size
            if offset >= file_size:
                return {
                    "status": "error",
                    "container_id": container_id,
                    "path": path,
                    "error": f"Offset {offset} is beyond file size {file_size}"
                }
            
            # Calculate actual length to read
            actual_length = min(length, file_size - offset)
            
            # Read the file content
            cmd = ['dd', f'if={path}', f'bs=1', f'skip={offset}', f'count={actual_length}']
            content_result = container.exec_run(
                cmd,
                demux=True
            )
            
            if content_result.exit_code != 0:
                return {
                    "status": "error",
                    "container_id": container_id,
                    "path": path,
                    "error": f"Failed to read file: {content_result.output[1] or 'Unknown error'}"
                }
            
            # Get the content
            content = content_result.output[0] or b''
            
            # Encode the content based on the requested encoding
            encoded_content = ''
            if encoding == 'base64':
                encoded_content = base64.b64encode(content).decode('ascii')
            elif encoding == 'utf-8':
                try:
                    encoded_content = content.decode('utf-8')
                except UnicodeDecodeError:
                    return {
                        "status": "error",
                        "container_id": container_id,
                        "path": path,
                        "error": "Content is not valid UTF-8, try using base64 encoding"
                    }
            elif encoding == 'latin-1':
                encoded_content = content.decode('latin-1')
            else:
                return {
                    "status": "error",
                    "container_id": container_id,
                    "path": path,
                    "error": f"Unsupported encoding: {encoding}"
                }
            
            # Get owner and group names if possible
            try:
                user_result = container.exec_run(['getent', 'passwd', str(uid)], demux=True)
                user = user_result.output[0].decode('utf-8').split(':')[0] if user_result.exit_code == 0 else str(uid)
                
                group_result = container.exec_run(['getent', 'group', str(gid)], demux=True)
                group = group_result.output[0].decode('utf-8').split(':')[0] if group_result.exit_code == 0 else str(gid)
            except:
                user = str(uid)
                group = str(gid)
            
            return {
                "status": "success",
                "container_id": container_id,
                "path": path,
                "exists": True,
                "is_file": True,
                "size": file_size,
                "content": encoded_content,
                "encoding": encoding,
                "truncated": (offset + actual_length) < file_size,
                "metadata": {
                    "mode": mode,
                    "uid": uid,
                    "gid": gid,
                    "user": user,
                    "group": group,
                    "mtime": datetime.fromtimestamp(mtime, tz=datetime.timezone.utc).isoformat()
                }
            }
            
        except ContainerError as e:
            if 'No such file or directory' in str(e):
                return {
                    "status": "success",
                    "container_id": container_id,
                    "path": path,
                    "exists": False,
                    "is_file": False
                }
            raise
            
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": error_msg}
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": "Docker daemon not available"}
        
    except Exception as e:
        error_msg = f"Unexpected error reading container file: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}

@Tool(
    name="write_container_file",
    description="Write content to a file in a container",
    parameters={
        'type': 'object',
        'properties': {
            'container_id': {
                'type': 'string',
                'description': 'ID or name of the container'
            },
            'path': {
                'type': 'string',
                'description': 'Path to the file in the container'
            },
            'content': {
                'type': 'string',
                'description': 'Content to write (base64-encoded if binary)'
            },
            'encoding': {
                'type': 'string',
                'enum': ['base64', 'utf-8', 'latin-1'],
                'default': 'base64',
                'description': 'Encoding of the content (default: base64)'
            },
            'mode': {
                'type': 'string',
                'pattern': '^[0-7]{3,4}$',
                'default': '644',
                'description': 'File mode in octal (e.g., 644 for rw-r--r--)'
            },
            'owner': {
                'type': 'string',
                'default': 'root:root',
                'description': 'Owner in format user:group (e.g., root:root)'
            },
            'mkdir': {
                'type': 'boolean',
                'default': False,
                'description': 'Create parent directories if they do not exist'
            }
        },
        'required': ['container_id', 'path', 'content']
    }
)
async def write_container_file(
    container_id: str,
    path: str,
    content: str,
    encoding: str = 'base64',
    mode: str = '644',
    owner: str = 'root:root',
    mkdir: bool = False
) -> Dict[str, Any]:
    """
    Write content to a file in a container.
    
    This function allows writing content to a file in a container's filesystem.
    It can create new files or overwrite existing ones, with support for different
    encodings and file permissions.
    
    Args:
        container_id: ID or name of the container
        path: Path to the file in the container
        content: Content to write (base64-encoded if binary)
        encoding: Encoding of the content (base64, utf-8, or latin-1)
        mode: File mode in octal (e.g., 644 for rw-r--r--)
        owner: Owner in format user:group (e.g., root:root)
        mkdir: Create parent directories if they do not exist
        
    Returns:
        Dictionary with operation status and metadata
        
    Example:
        >>> await write_container_file(
        ...     container_id="my-container",
        ...     path="/app/config.json",
        ...     content="eyJkYiI6ICJteXNxbCJ9",
        ...     encoding="base64",
        ...     mode="644",
        ...     owner="app:app"
        ... )
        {
            "status": "success",
            "container_id": "a1b2c3d4e5f6",
            "path": "/app/config.json",
            "wrote_bytes": 15,
            "message": "File written successfully"
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        try:
            container = client.containers.get(container_id)
        except NotFound:
            return {
                "status": "error",
                "container_id": container_id,
                "error": f"Container not found: {container_id}"
            }
        
        # Normalize path
        path = os.path.normpath(path).replace('\\', '/')
        dirname = os.path.dirname(path)
        
        # Decode content based on encoding
        try:
            if encoding == 'base64':
                file_content = base64.b64decode(content)
            elif encoding == 'utf-8':
                file_content = content.encode('utf-8')
            elif encoding == 'latin-1':
                file_content = content.encode('latin-1')
            else:
                return {
                    "status": "error",
                    "container_id": container_id,
                    "path": path,
                    "error": f"Unsupported encoding: {encoding}"
                }
        except Exception as e:
            return {
                "status": "error",
                "container_id": container_id,
                "path": path,
                "error": f"Failed to decode content: {str(e)}"
            }
        
        # Create parent directories if needed
        if mkdir and dirname != '/':
            mkdir_cmd = ['mkdir', '-p', dirname]
            mkdir_result = container.exec_run(mkdir_cmd, demux=True)
            if mkdir_result.exit_code != 0:
                error_output = mkdir_result.output[1] or b''
                return {
                    "status": "error",
                    "container_id": container_id,
                    "path": path,
                    "error": f"Failed to create directory: {error_output.decode('utf-8', errors='replace').strip()}"
                }
        
        # Create a temporary file to hold the content
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(file_content)
            tmp_file_path = tmp_file.name
        
        try:
            # Copy the file to the container
            with open(tmp_file_path, 'rb') as f:
                container.put_archive(
                    path=dirname,
                    data=_create_tar_archive(f, os.path.basename(path))
                )
            
            # Set file permissions
            chmod_cmd = ['chmod', mode, path]
            chmod_result = container.exec_run(chmod_cmd, demux=True)
            if chmod_result.exit_code != 0:
                error_output = chmod_result.output[1] or b''
                return {
                    "status": "error",
                    "container_id": container_id,
                    "path": path,
                    "error": f"Failed to set file permissions: {error_output.decode('utf-8', errors='replace').strip()}"
                }
            
            # Set file ownership
            chown_cmd = ['chown', owner, path]
            chown_result = container.exec_run(chown_cmd, demux=True)
            if chown_result.exit_code != 0:
                error_output = chown_result.output[1] or b''
                return {
                    "status": "error",
                    "container_id": container_id,
                    "path": path,
                    "warning": f"Failed to set file ownership: {error_output.decode('utf-8', errors='replace').strip()}",
                    "wrote_bytes": len(file_content)
                }
            
            return {
                "status": "success",
                "container_id": container_id,
                "path": path,
                "wrote_bytes": len(file_content),
                "message": "File written successfully"
            }
            
        finally:
            # Clean up the temporary file
            try:
                os.unlink(tmp_file_path)
            except:
                pass
            
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": error_msg}
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": "Docker daemon not available"}
        
    except Exception as e:
        error_msg = f"Unexpected error writing container file: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}

def _create_tar_archive(file_obj: BinaryIO, filename: str) -> bytes:
    """
    Create a tar archive containing a single file.
    
    Args:
        file_obj: File-like object to include in the archive
        filename: Name of the file in the archive
        
    Returns:
        Bytes containing the tar archive
    """
    file_data = file_obj.read()
    
    with BytesIO() as tar_buffer:
        with tarfile.open(fileobj=tar_buffer, mode='w') as tar:
            # Create a TarInfo object for the file
            tarinfo = tarfile.TarInfo(name=filename)
            tarinfo.size = len(file_data)
            tarinfo.mtime = int(time.time())
            tarinfo.mode = 0o644
            
            # Add the file to the archive
            tar.addfile(tarinfo, fileobj=BytesIO(file_data))
        
        # Return the tar archive as bytes
        return tar_buffer.getvalue()
