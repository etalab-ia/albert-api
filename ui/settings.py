from functools import lru_cache
import os
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings
import yaml


class ConfigBaseModel(BaseModel):
    class Config:
        extra = "allow"


class Database(ConfigBaseModel):
    url: str = "postgresql+asyncpg://postgres:changeme@postgres:5432/ui"


class Config(ConfigBaseModel):
    cache_ttl: int = 1800  # 30 minutes
    api_url: str = "http://localhost:8080"
    max_token_expiration_days: int = 60  # days
    database: Database = Field(default_factory=Database)
    master_username: str = "master"


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
        config = Config(**yaml.safe_load(stream=stream)["ui"])
        stream.close()

        # Merge config values with existing values
        for key, value in config.__dict__.items():
            if key not in values.__dict__.keys():
                setattr(values, key, value)

        return values


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
