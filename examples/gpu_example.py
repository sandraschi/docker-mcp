"""
GPU Tools Example

This script demonstrates how to use the GPU management tools in DockerMCP.
It shows how to list GPUs, monitor usage, and run GPU-accelerated containers.
"""
import asyncio
import json
from datetime import datetime

from dockermcp.tools.gpu import create_gpu_container, get_container_gpu_info, get_gpu_info, list_gpus, monitor_gpu_usage


async def main():
    """Run GPU tool examples."""
    print("=" * 80)
    print("DockerMCP GPU Tools Example")
    print("=" * 80)

    # Example 1: List available GPUs
    print("\n1. Listing available GPUs...")
    gpus = await list_gpus(detailed=True)
    print(f"Found {gpus['total_gpus']} GPU(s):")
    for i, gpu in enumerate(gpus['gpus']):
        print(f"  {i+1}. {gpu['name']} (ID: {gpu['id']})")
        print(f"     Memory: {gpu['memory_used']/1024**3:.1f}GB / {gpu['memory_total']/1024**3:.1f}GB used")
        print(f"     Utilization: {gpu['utilization_gpu']}% GPU, {gpu['utilization_memory']}% Memory")
        print(f"     Temperature: {gpu['temperature']}°C, Power: {gpu['power_draw']}W / {gpu['power_limit']}W")

    if gpus['total_gpus'] == 0:
        print("No GPUs found. Exiting...")
        return

    # Example 2: Get detailed info about the first GPU
    print("\n2. Getting detailed info for first GPU...")
    gpu_info = await get_gpu_info(gpu_id="0")
    if gpu_info['status'] == 'success':
        print(json.dumps(gpu_info['gpu'], indent=2, default=str))
    else:
        print(f"Error: {gpu_info.get('error', 'Unknown error')}")

    # Example 3: Monitor GPU usage
    print("\n3. Monitoring GPU usage for 10 seconds... (press Ctrl+C to skip)")
    try:
        monitor_result = await monitor_gpu_usage(interval=1.0, duration=10.0)
        if monitor_result['status'] == 'success':
            print(f"\nCollected {monitor_result['sample_count']} samples:")
            for sample in monitor_result['samples'][:3]:  # Show first 3 samples
                print(f"  {sample['timestamp']} - "
                      f"GPU: {sample['gpus'][0]['utilization_gpu']}%, "
                      f"Mem: {sample['gpus'][0]['memory_used']/1024**3:.1f}GB")
            if len(monitor_result['samples']) > 3:
                print(f"  ... and {len(monitor_result['samples']) - 3} more samples")
    except asyncio.CancelledError:
        print("\nMonitoring interrupted by user")

    # Example 4: Run a GPU-accelerated container
    print("\n4. Running a GPU-accelerated container...")
    container = await create_gpu_container(
        image="nvidia/cuda:11.0-base",
        command="nvidia-smi",
        gpu_ids=[0],  # Use first GPU
        name=f"gpu-test-{int(datetime.now().timestamp())}",
        detach=False,
        auto_remove=True
    )

    if container['status'] == 'success':
        if 'output' in container:
            print("Container output:")
            print(container['output'].decode('utf-8') if hasattr(container['output'], 'decode') else container['output'])
        else:
            print(f"Container started with ID: {container.get('container_id')}")
    else:
        print(f"Error: {container.get('error', 'Failed to start container')}")

    # Example 5: Get container GPU info
    if container.get('container_id'):
        print("\n5. Getting container GPU info...")
        container_info = await get_container_gpu_info(container_id=container['container_id'])
        if container_info['status'] == 'success':
            print(f"Container {container_info['container_id']} has GPU access: {container_info['has_gpu_access']}")
            if container_info.get('gpus'):
                print(f"Assigned GPUs: {', '.join(gpu['id'] for gpu in container_info['gpus'])}")
        else:
            print(f"Error: {container_info.get('error', 'Failed to get container info')}")

if __name__ == "__main__":
    asyncio.run(main())
