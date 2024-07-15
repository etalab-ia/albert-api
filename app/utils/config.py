import os
import logging
import sys

import yaml

sys.path.append("..")
from schemas.config import Config


def load_and_validate_yaml(file_path: str) -> Config:
    with open(file_path, "r") as file:
        data = yaml.safe_load(file)
    return Config(**data)


logging.basicConfig(format="%(levelname)s:%(asctime)s: %(message)s", level=logging.INFO)

CONFIG_FILE = os.getenv("CONFIG_FILE", "../config.yml")
logging.info(f"loading configuration file: {CONFIG_FILE}")
CONFIG = load_and_validate_yaml(CONFIG_FILE)

API_KEYS = [key.key for key in CONFIG.auth.keys]
logging.info(f"{len(API_KEYS)} API keys found in the configuration file.")
