import os
import logging
import yaml

from app.schemas.config import Config

logging.basicConfig(format="%(levelname)s:%(asctime)s: %(message)s", level=logging.INFO)

CONFIG_FILE = os.getenv("CONFIG_FILE", "config.yml")
logging.info(f"loading configuration file: {CONFIG_FILE}")
CONFIG = Config(**yaml.safe_load(open(CONFIG_FILE, "r")))

# Metadata
APP_CONTACT_URL = os.getenv("APP_CONTACT_URL")
APP_CONTACT_EMAIL = os.getenv("APP_CONTACT_EMAIL")
APP_VERSION = os.getenv("APP_VERSION", "0.0.0")
APP_DESCRIPTION = os.getenv(
    "APP_DESCRIPTION",
    "[See documentation](https://github.com/etalab-ia/albert-api/blob/main/README.md)",
)