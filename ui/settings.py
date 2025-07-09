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
    ELASTICSEARCH = "elasticsearch"
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
    default_model: Optional[str] = None

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
            lines = file.readlines()

        non_comment_lines = [line for line in lines if not line.lstrip().startswith("#")]
        file_content = cls.replace_all_variables_in_file("".join(non_comment_lines))
        config = Config(**yaml.safe_load(file_content))

        values.auth = config.auth
        values.playground = config.playground
        values.databases = config.databases

        return values

    @classmethod
    def replace_all_variables_in_file(cls, file_content):
        env_variable_pattern = re.compile(r"\${([A-Z0-9_]+)(:-[^}]*)?}")

        def replace_env_var(match):
            env_variable_definition = match.group(0)
            env_variable_name = match.group(1)
            default_env_variable_value = match.group(2)[2:] if match.group(2) else None

            env_variable_value = os.getenv(env_variable_name)

            if env_variable_value is not None and env_variable_value != "":
                return env_variable_value
            elif default_env_variable_value is not None:
                return default_env_variable_value
            else:
                logging.warning(f"Environment variable {env_variable_name} not found or empty to replace {env_variable_definition}.")
                return env_variable_definition

        file_content = env_variable_pattern.sub(replace_env_var, file_content)
        return file_content


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
