import logging
import os

# Configure application-wide logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger("pk_pipeline")

# Mock configurations
USE_MOCKS = os.getenv("USE_MOCKS", "True").lower() in ("true", "1", "yes")

class Config:
    TEMP_IMAGE_DIR = "/tmp/pk_pipeline_images"
    os.makedirs(TEMP_IMAGE_DIR, exist_ok=True)
