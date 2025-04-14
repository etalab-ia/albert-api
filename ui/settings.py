from functools import lru_cache
import logging
import os
import re
from typing import Any, Optional

from pydantic import BaseModel, field_validator, model_validator
from pydantic_settings import BaseSettings
import yaml


class ConfigBaseModel(BaseModel):
    class Config:
        extra = "allow"


class Auth(ConfigBaseModel):
    master_username: str = "master"


class Playground(ConfigBaseModel):
    api_url: str = "http://localhost:8000"
    home_url: str = "http://localhost:8501"
    max_api_key_expiration_days: Optional[int] = None
    cache_ttl: int = 1800  # 30 minutes
    database_url: str = "postgresql+asyncpg://postgres:changeme@localhost:5432/ui"


class Config(ConfigBaseModel):
    auth: Auth
    playground: Playground


class Settings(BaseSettings):
    config_file: str = "config.yml"

    class Config:
        extra = "allow"

    @field_validator("config_file", mode="before")
    def config_file_exists(cls, config_file):
        assert os.path.exists(path=config_file), "Config file not found."
        return config_file

    @model_validator(mode="after")
    def setup_config(cls, values) -> Any:
        with open(file=values.config_file, mode="r") as file:
            file_content = file.read()
            file.close()

        # replace environment variables (pattern: ${VARIABLE_NAME})
        for match in set(re.findall(pattern=r"\${[A-Z_]+}", string=file_content)):
            variable = match.replace("${", "").replace("}", "")
            if not os.getenv(variable):
                logging.warning(f"Environment variable {variable} not found or empty to replace {match}.")
            file_content = file_content.replace(match, os.getenv(variable, match))

        config = Config(**yaml.safe_load(file_content))

        values.auth = config.auth
        values.playground = config.playground

        return values


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
