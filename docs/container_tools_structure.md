# Container Tools Module Structure

This document outlines the current structure of the container tools module and its components.

## Core Modules

1. **container_tools.py**
   - Main module with comprehensive container management functions
   - Contains implementations for:
     - Container lifecycle (create, start, stop, restart, remove)
     - Log management
     - Process management (top, exec)
     - Inspection and monitoring
     - Resource usage statistics

2. **Specialized Modules**
   - `container_lifecycle.py`: Container lifecycle operations
   - `container_logs.py`: Log streaming and management
   - `container_exec.py`: Command execution in containers
   - `container_inspect.py`: Container inspection and details
   - `container_models.py`: Pydantic models for request/response
   - `container_tools_registry.py`: Tool registration for FastMCP

## Current Issues

1. **Duplication**: `container_tools.py` contains implementations that overlap with specialized modules
2. **Inconsistency**: Mixed patterns between direct implementation and module-based organization
3. **Documentation**: Inconsistent docstrings and examples across modules

## Proposed Structure

1. **container_tools.py** (Facade)
   - Re-exports functionality from specialized modules
   - Provides backward compatibility
   - Contains only high-level documentation

2. **Specialized Modules**
   - Each module focuses on a specific aspect of container management
   - Clear separation of concerns
   - Consistent documentation and examples

3. **Models and Types**
   - Centralized in `container_models.py`
   - Used consistently across all modules

4. **Tool Registration**
   - Handled by `container_tools_registry.py`
   - Imports and registers tools from specialized modules
