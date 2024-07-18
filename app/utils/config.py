import os
import logging
import sys

import yaml

sys.path.append("..")
from schemas.config import Config

logging.basicConfig(format="%(levelname)s:%(asctime)s: %(message)s", level=logging.INFO)

CONFIG_FILE = os.getenv("CONFIG_FILE", "../config.yml")
logging.info(f"loading configuration file: {CONFIG_FILE}")
CONFIG = Config(**yaml.safe_load(open(CONFIG_FILE, "r")))
