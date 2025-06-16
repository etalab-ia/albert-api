from enum import Enum
from functools import lru_cache
import logging
import os
import re
from types import SimpleNamespace
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_settings import BaseSettings
import yaml


class DatabaseType(str, Enum):
    QDRANT = "qdrant"
    REDIS = "redis"
    SQL = "sql"


class ConfigBaseModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class MenuItems(ConfigBaseModel):
    get_help: Optional[str] = None
    report_a_bug: Optional[str] = None
    about: Optional[str] = None


class DatabaseSQLArgs(ConfigBaseModel):
    url: str = Field(pattern=r"^postgresql|^sqlite")

    @field_validator("url", mode="after")
    def validate_url(cls, url):
        if url.startswith("postgresql+asyncpg://"):
            logging.warning("PostgreSQL connection must be sync, force sync connection.")
            return url.replace("postgresql+asyncpg", "postgresql")

        if url.startswith("sqlite+aiosqlite://"):
            logging.warning("SQLite connection must be sync, force sync connection.")
            return url.replace("sqlite+aiosqlite", "sqlite")

        return url


class Database(ConfigBaseModel):
    type: DatabaseType
    context: str = "playground"
    args: dict = {}

    @model_validator(mode="after")
    def format(cls, values):
        if values.type == DatabaseType.SQL and values.context == "playground":
            values.args = DatabaseSQLArgs(**values.args).model_dump()

        return values


class Auth(ConfigBaseModel):
    master_username: str = "master"
    max_token_expiration_days: Optional[int] = Field(default=None, ge=0)


class Playground(ConfigBaseModel):
    api_url: str = "http://localhost:8000"
    home_url: str = "http://localhost:8501"
    page_icon: str = "https://github.com/etalab-ia/albert-api/blob/main/docs/assets/logo.png?raw=true"
    menu_items: MenuItems = MenuItems()
    logo: str = "https://github.com/etalab-ia/albert-api/blob/main/docs/assets/logo.png?raw=true"
    cache_ttl: int = 1800  # 30 minutes


class Config(ConfigBaseModel):
    auth: Auth
    playground: Playground
    databases: List[Database]

    @model_validator(mode="after")
    def validate_databases(cls, values) -> Any:
        sql_databases = [database for database in values.databases if database.type == DatabaseType.SQL and database.context == "playground"]
        if len(sql_databases) > 1:
            raise ValueError("There must be only one SQL database with the `playground` context. If your configuration files contains multiple SQL databases, please specify the context keyword for other SQL databases.")  # fmt: off
        if len(sql_databases) == 0:
            raise ValueError("There must be at least one SQL database.")

        values.databases = SimpleNamespace()
        values.databases.sql = sql_databases[0]

        return values


class Settings(BaseSettings):
    model_config = ConfigDict(extra="allow")

    config_file: str = "config.yml"

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
            if os.getenv(variable) is None or os.getenv(variable) == "":
                logging.warning(f"Environment variable {variable} not found or empty to replace {match}.")
            file_content = file_content.replace(match, os.getenv(variable, match))

        config = Config(**yaml.safe_load(file_content))

        values.auth = config.auth
        values.playground = config.playground
        values.databases = config.databases

        return values


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
