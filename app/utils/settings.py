import os
from functools import lru_cache

from dotenv import load_dotenv

from app.schemas.core.settings import Settings

env_file = os.getenv("ENV_FILE", ".env")
load_dotenv(env_file)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
