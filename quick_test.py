import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

print("Testing container models import...")
try:
    from dockermcp.tools.containers.container_models import ContainerInfo
    print("✅ Container models OK")
except Exception as e:
    print(f"❌ Container models error: {e}")

print("Testing image models import...")
try:
    from dockermcp.tools.images.image_models import ImageInfo  
    print("✅ Image models OK")
except Exception as e:
    print(f"❌ Image models error: {e}")

print("Testing network models import...")
try:
    from dockermcp.tools.networks.network_models import NetworkInfo
    print("✅ Network models OK") 
except Exception as e:
    print(f"❌ Network models error: {e}")

print("Testing volumes models import...")
try:
    from dockermcp.tools.volumes.volume_models import VolumeInfo
    print("✅ Volume models OK")
except Exception as e:
    print(f"❌ Volume models error: {e}")

print("Testing system models import...")
try:
    from dockermcp.tools.system.system_models import SystemInfo
    print("✅ System models OK")
except Exception as e:
    print(f"❌ System models error: {e}")
    
print("Testing compose models import...")
try:
    from dockermcp.tools.compose.compose_models import ComposeProjectInfo
    print("✅ Compose models OK")
except Exception as e:
    print(f"❌ Compose models error: {e}")

print("Done.")
