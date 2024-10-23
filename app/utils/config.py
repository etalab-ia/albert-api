import logging
import os

import yaml

from app.schemas.config import Config
from app.schemas.models import EMBEDDINGS_MODEL_TYPE, LANGUAGE_MODEL_TYPE

logging.basicConfig(format="%(levelname)s:%(asctime)s:%(name)s: %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOG_LEVEL", logging.DEBUG))

# Configuration
CONFIG_FILE = os.getenv("CONFIG_FILE", "config.yml")
assert os.path.exists(CONFIG_FILE), f"error: configuration file {CONFIG_FILE} not found"
logger.info(f"loading configuration file: {CONFIG_FILE}")
CONFIG = Config(**yaml.safe_load(open(CONFIG_FILE, "r")))

# Metadata
APP_CONTACT_URL = os.getenv("APP_CONTACT_URL")
APP_CONTACT_EMAIL = os.getenv("APP_CONTACT_EMAIL")
APP_VERSION = os.getenv("APP_VERSION", "0.0.0")
APP_DESCRIPTION = os.getenv(
    "APP_DESCRIPTION",
    "[See documentation](https://github.com/etalab-ia/albert-api/blob/main/README.md)",
)

# Models
DEFAULT_INTERNET_LANGUAGE_MODEL_URL = os.getenv(
    "DEFAULT_INTERNET_LANGUAGE_MODEL_URL", [model.url for model in CONFIG.models if model.type == LANGUAGE_MODEL_TYPE][0]
)
DEFAULT_INTERNET_EMBEDDINGS_MODEL_URL = os.getenv(
    "DEFAULT_INTERNET_EMBEDDINGS_MODEL_URL", [model.url for model in CONFIG.models if model.type == EMBEDDINGS_MODEL_TYPE][0]
)
assert DEFAULT_INTERNET_LANGUAGE_MODEL_URL in [model.url for model in CONFIG.models], "Default internet language model not found."
assert DEFAULT_INTERNET_EMBEDDINGS_MODEL_URL in [model.url for model in CONFIG.models], "Default internet embeddings model not found."
assert DEFAULT_INTERNET_LANGUAGE_MODEL_URL in [
    model.url for model in CONFIG.models if model.type == LANGUAGE_MODEL_TYPE
], "Default internet language model wrong type."
assert DEFAULT_INTERNET_EMBEDDINGS_MODEL_URL in [
    model.url for model in CONFIG.models if model.type == EMBEDDINGS_MODEL_TYPE
], "Default internet embeddings model wrong type."

logger.info(f"default internet language model url: {DEFAULT_INTERNET_LANGUAGE_MODEL_URL}")
logger.info(f"default internet embeddings model url: {DEFAULT_INTERNET_EMBEDDINGS_MODEL_URL}")

# Rate limit
GLOBAL_RATE_LIMIT = os.getenv("GLOBAL_RATE_LIMIT", "100/minute")
DEFAULT_RATE_LIMIT = os.getenv("DEFAULT_RATE_LIMIT", "10/minute")
