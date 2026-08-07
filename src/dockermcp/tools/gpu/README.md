# GPU Management Tools for DockerMCP

This module provides tools for managing NVIDIA GPU resources in Docker containers, including GPU monitoring, container configuration, and resource management.

## Features

- **GPU Discovery**: List available GPUs and their properties
- **Monitoring**: Monitor GPU usage in real-time
- **Container Integration**: Create and manage GPU-accelerated containers
- **Resource Management**: Allocate specific GPUs to containers
- **Metrics Collection**: Gather GPU metrics and statistics

## Prerequisites

- NVIDIA GPU with appropriate drivers installed
- NVIDIA Container Toolkit installed on the host system
- Docker installed and configured to use the NVIDIA runtime

## Installation

1. Install the required dependencies:

```bash
pip install -r requirements-gpu.txt
```

2. Verify that the NVIDIA Container Toolkit is properly installed:

```bash
docker run --gpus all nvidia/cuda:11.0-base nvidia-smi
```

## Available Tools

### `list_gpus`

List all available NVIDIA GPUs and their current status.

**Parameters:**
- `refresh` (bool, optional): Whether to refresh the GPU information cache. Defaults to False.
- `detailed` (bool, optional): Whether to include detailed GPU information. Defaults to False.

**Example:**
```python
result = await list_gpus()
print(json.dumps(result, indent=2))
```

### `get_gpu_info`

Get detailed information about a specific GPU.

**Parameters:**
- `gpu_id` (str): ID of the GPU to get information about
- `refresh` (bool, optional): Whether to refresh the GPU information cache. Defaults to False.

**Example:**
```python
result = await get_gpu_info(gpu_id="0")
print(json.dumps(result, indent=2))
```

### `monitor_gpu_usage`

Monitor GPU usage in real-time.

**Parameters:**
- `interval` (float, optional): Polling interval in seconds. Defaults to 5.0.
- `duration` (float, optional): Total duration to monitor in seconds. Defaults to 60.0.

**Example:**
```python
result = await monitor_gpu_usage(interval=2.0, duration=10.0)
print(json.dumps(result, indent=2))
```

### `create_gpu_container`

Create and start a GPU-accelerated Docker container.

**Parameters:**
- `image` (str): Docker image to use
- `command` (str, optional): Command to run in the container
- `gpu_ids` (Union[List[Union[int, str]], str], optional): List of GPU IDs to use or 'all'. Defaults to 'all'.
- `count` (Union[int, str], optional): Number of GPUs to use or 'all'. Defaults to None.
- `runtime` (str, optional): Container runtime to use. Defaults to 'nvidia'.
- `environment` (Dict[str, str], optional): Environment variables to set in the container
- `name` (str, optional): Name for the container
- `detach` (bool, optional): Run container in detached mode. Defaults to True.
- `auto_remove` (bool, optional): Automatically remove the container when it exits. Defaults to False.
- `shm_size` (str, optional): Size of /dev/shm. Defaults to '2g'.
- `volumes` (Dict[str, str], optional): Volume mappings (host_path:container_path)
- `ports` (Dict[str, str], optional): Port mappings (host_port:container_port)

**Example:**
```python
result = await create_gpu_container(image="nvidia/cuda:11.0-base", command="nvidia-smi", gpu_ids=[0], name="gpu-test")
print(json.dumps(result, indent=2))
```

### `get_container_gpu_info`

Get GPU information for a running container.

**Parameters:**
- `container_id` (str): Container ID or name

**Example:**
```python
result = await get_container_gpu_info(container_id="gpu-test")
print(json.dumps(result, indent=2))
```

## Example Workflow

### 1. List available GPUs

```python
# List all available GPUs
gpus = await list_gpus()
print(f"Available GPUs: {gpus['total_gpus']}")
for gpu in gpus["gpus"]:
    print(
        f"- {gpu['name']} (ID: {gpu['id']}): {gpu['memory_used'] / 1024**3:.1f}GB / {gpu['memory_total'] / 1024**3:.1f}GB used"
    )
```

### 2. Run a GPU-accelerated container

```python
# Run a simple CUDA container
result = await create_gpu_container(
    image="nvidia/cuda:11.0-base",
    command="nvidia-smi",
    gpu_ids=[0],  # Use first GPU
    name="cuda-test",
    detach=False,  # Wait for command to complete
)
print(result["output"])  # Prints nvidia-smi output
```

### 3. Monitor GPU usage

```python
# Monitor GPU usage for 30 seconds
result = await monitor_gpu_usage(interval=1.0, duration=30.0)
for sample in result["samples"]:
    print(
        f"{sample['timestamp']} - GPU Util: {sample['gpus'][0]['utilization_gpu']}%, "
        f"Mem Used: {sample['gpus'][0]['memory_used'] / 1024**3:.1f}GB"
    )
```

## Error Handling

All functions return a dictionary with a `status` field indicating success or failure:
- `status='success'`: Operation completed successfully
- `status='error'`: An error occurred (check the `error` field for details)

## Troubleshooting

### Common Issues

1. **No GPUs detected**
   - Verify that NVIDIA drivers are installed: `nvidia-smi`
   - Check that the NVIDIA Container Toolkit is installed
   - Ensure Docker is configured to use the NVIDIA runtime

2. **Permission denied when accessing GPUs**
   - Make sure the user has permission to access the NVIDIA devices
   - Try running with `sudo` or add the user to the `docker` group

3. **CUDA version mismatch**
   - Ensure the CUDA version in your container matches the host driver version
   - Check with `nvidia-smi` on the host and `nvidia-smi` in the container

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.
