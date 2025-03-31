from functools import lru_cache
import os
from typing import Any, Literal, Optional

from pydantic import BaseModel, field_validator, model_validator
from pydantic_settings import BaseSettings
import yaml


class ConfigBaseModel(BaseModel):
    class Config:
        extra = "allow"


class Auth(ConfigBaseModel):
    master_username: str = "master"


class Playground(ConfigBaseModel):
    api_url: str = "http://localhost:8080"
    max_api_key_expiration_days: Optional[int] = None
    cache_ttl: int = 1800  # 30 minutes
    database_url: str = "postgresql+asyncpg://postgres:changeme@localhost:5432/ui"


class Config(ConfigBaseModel):
    auth: Auth
    playground: Playground


class Settings(BaseSettings):
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    config_file: str = "config.yml"

    class Config:
        extra = "allow"

    @field_validator("config_file", mode="before")
    def config_file_exists(cls, config_file):
        assert os.path.exists(path=config_file), "Config file not found."
        return config_file

    @model_validator(mode="after")
    def setup_config(cls, values) -> Any:
        stream = open(file=values.config_file, mode="r")
        config = Config(**yaml.safe_load(stream=stream))
        stream.close()

        values.auth = config.auth
        values.playground = config.playground

        return values


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
