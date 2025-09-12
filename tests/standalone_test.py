"""
Standalone test for container inspection functionality.
This file contains everything needed to test the inspect_container function.
"""
import asyncio
import json
import logging
import docker
from typing import Dict, Any, Optional, List, TypeVar, Type, cast
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Mock Tool decorator for testing
class Tool:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
    
    def __call__(self, func):
        # Just return the function as-is for testing
        return func

# Mock BaseModel for Pydantic models
class BaseModel:
    def __init__(self, **data):
        for key, value in data.items():
            setattr(self, key, value)
    
    def dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

# Mock the Tool decorator at the module level
import sys
from unittest.mock import MagicMock

# Create a mock module for fastmcp.tools
fastmcp_tools = MagicMock()
fastmcp_tools.Tool = Tool
sys.modules['fastmcp.tools'] = fastmcp_tools

# Create a mock module for fastmcp.exceptions
fastmcp_exceptions = MagicMock()
fastmcp_exceptions.ToolError = Exception
sys.modules['fastmcp.exceptions'] = fastmcp_exceptions

# Import the function we want to test
from dockermcp.tools.containers.container_inspect_v2 import inspect_container

async def test_inspect():
    """Test the inspect_container function with a running container."""
    try:
        # Get a list of running containers
        client = docker.from_env()
        containers = client.containers.list(limit=1)
        
        if not containers:
            logger.warning("No running containers found. Starting a test container...")
            # Start a test container if none are running
            container = client.containers.run(
                "hello-world",
                name="test-container",
                detach=True,
                remove=True
            )
            container_id = container.id
            logger.info(f"Started test container: {container_id}")
        else:
            container_id = containers[0].id
            logger.info(f"Using existing container: {container_id}")
        
        # Test basic inspection
        logger.info("Testing inspect_container...")
        result = await inspect_container(
            container_id=container_id,
            include_stats=True,
            include_logs=True,
            log_tail=5
        )
        
        # Print results
        print("\n=== Inspection Results ===")
        print(f"Success: {result.get('success')}")
        print(f"Container ID: {result.get('container_id')}")
        print(f"Name: {result.get('name')}")
        print(f"Status: {result.get('status')}")
        print(f"Image: {result.get('image')}")
        
        if 'stats' in result and result['stats']:
            print("\n=== Stats ===")
            stats = result['stats']
            print(f"CPU: {stats.get('cpu_percent')}%")
            print(f"Memory: {stats.get('memory_usage')}MB / {stats.get('memory_limit')}MB ({stats.get('memory_percent')}%)")
        
        if 'logs' in result and result['logs']:
            print("\n=== Logs (last 5 lines) ===")
            for line in result['logs'][-5:]:
                print(f"  {line}")
        
        print("\nTest completed successfully!")
        return result
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    # Add the src directory to Python path
    import sys
    from pathlib import Path
    src_path = str(Path(__file__).parent.parent / 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    asyncio.run(test_inspect())
