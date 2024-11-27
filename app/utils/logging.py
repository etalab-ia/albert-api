import logging
from app.utils.settings import settings

logging.basicConfig(format="%(levelname)s:%(asctime)s:%(name)s: %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(settings.log_level)
