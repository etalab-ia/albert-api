
import os
import logging

import yaml

logging.basicConfig(format="%(levelname)s:%(asctime)s: %(message)s", level=logging.INFO)

config_path = os.path.join(os.getenv("CONFIG_FILE", "../config.yml"))
logging.info(f"loading configuration file: {config_path}")
CONFIG = yaml.safe_load(open(config_path, "r"))

# @TODO: add assertions for config file