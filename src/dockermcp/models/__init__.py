"""
Pydantic models for request/response validation.

This package contains all data models used for API request/response validation.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

class BaseResponse(BaseModel):
    """Base response model with common fields."""
    success: bool
    message: str
    error: Optional[str] = None

class ContainerInfo(BaseModel):
    """Container information model."""
    id: str
    name: str
    status: str
    image: str
    created: str
    ports: Optional[Dict[str, Any]] = None
    labels: Optional[Dict[str, str]] = None

class ImageInfo(BaseModel):
    """Image information model."""
    id: str
    tags: List[str]
    created: str
    size: int
    virtual_size: int

class NetworkInfo(BaseModel):
    """Network information model."""
    id: str
    name: str
    driver: str
    scope: str
    ipam: Dict[str, Any]
    containers: Optional[List[Dict[str, str]]] = None
    created: Optional[str] = None
    labels: Optional[Dict[str, str]] = None

class VolumeInfo(BaseModel):
    """Volume information model."""
    name: str
    driver: str
    mountpoint: str
    created: Optional[str] = None
    scope: Optional[str] = None
    labels: Optional[Dict[str, str]] = None
    options: Optional[Dict[str, str]] = None
    usage_data: Optional[Dict[str, Any]] = None

class SystemInfo(BaseModel):
    """System information model."""
    containers: int
    containers_running: int
    containers_paused: int
    containers_stopped: int
    images: int
    driver: str
    os: str
    architecture: str
    cpus: int
    memory: int
    docker_root_dir: str
