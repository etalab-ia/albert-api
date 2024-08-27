import os
import logging
import yaml

from app.schemas.config import Config

logging.basicConfig(format="%(levelname)s:%(asctime)s:%(name)s: %(message)s", level=logging.INFO)
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(os.getenv("LOG_LEVEL", logging.DEBUG))

# Configuration
CONFIG_FILE = os.getenv("CONFIG_FILE", "config.yml")
assert os.path.exists(CONFIG_FILE), f"error: configuration file {CONFIG_FILE} not found"
LOGGER.info(f"loading configuration file: {CONFIG_FILE}")
CONFIG = Config(**yaml.safe_load(open(CONFIG_FILE, "r")))

# Metadata
APP_CONTACT_URL = os.getenv("APP_CONTACT_URL")
APP_CONTACT_EMAIL = os.getenv("APP_CONTACT_EMAIL")
APP_VERSION = os.getenv("APP_VERSION", "0.0.0")
APP_DESCRIPTION = os.getenv(
    "APP_DESCRIPTION",
    "[See documentation](https://github.com/etalab-ia/albert-api/blob/main/README.md)",
)
