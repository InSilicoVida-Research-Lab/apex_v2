import logging
import os
import tempfile
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Configure application-wide logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger("pk_pipeline")
logging.getLogger("pdfminer").setLevel(logging.WARNING)

# Mock configurations
USE_MOCKS = os.getenv("USE_MOCKS", "False").lower() in ("true", "1", "yes")

class Config:
    TEMP_IMAGE_DIR = os.getenv(
        "TEMP_IMAGE_DIR",
        os.path.join(tempfile.gettempdir(), "pk_pipeline_images")
    )
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
    
    # Priority endpoints
    SGLANG_LOCAL_URL = os.getenv("SGLANG_LOCAL_URL", "http://127.0.0.1:30000").rstrip("/")
    DGX_SGLANG_URL = os.getenv("DGX_SGLANG_URL", "http://100.85.128.70:30001").rstrip("/")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "http://100.85.128.70:30001/v1").rstrip("/")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "EMPTY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "Qwen/Qwen3.8-27B-FP8")
    FORCE_BACKEND = os.getenv("FORCE_BACKEND", "auto").lower().strip()

    os.makedirs(TEMP_IMAGE_DIR, exist_ok=True)
