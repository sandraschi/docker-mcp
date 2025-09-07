import sys
import os
from dockermcp.logging_config import logger, configure_logging

# Configure logging
configure_logging()

sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
logger.info("Testing container models import...")
try:
    from dockermcp.tools.containers.container_models import ContainerInfo
logger.info("✅ Container models OK")
except Exception as e:
logger.info(f"❌ Container models error: {e}")
logger.info("Testing image models import...")
try:
    from dockermcp.tools.images.image_models import ImageInfo  
logger.info("✅ Image models OK")
except Exception as e:
logger.info(f"❌ Image models error: {e}")
logger.info("Testing network models import...")
try:
    from dockermcp.tools.networks.network_models import NetworkInfo
logger.info("✅ Network models OK") 
except Exception as e:
logger.info(f"❌ Network models error: {e}")
logger.info("Testing volumes models import...")
try:
    from dockermcp.tools.volumes.volume_models import VolumeInfo
logger.info("✅ Volume models OK")
except Exception as e:
logger.info(f"❌ Volume models error: {e}")
logger.info("Testing system models import...")
try:
    from dockermcp.tools.system.system_models import SystemInfo
logger.info("✅ System models OK")
except Exception as e:
logger.info(f"❌ System models error: {e}")
logger.info("Testing compose models import...")
try:
    from dockermcp.tools.compose.compose_models import ComposeProjectInfo
logger.info("✅ Compose models OK")
except Exception as e:
logger.info(f"❌ Compose models error: {e}")
logger.info("Done.")
