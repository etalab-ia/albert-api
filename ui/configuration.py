from functools import lru_cache
import logging
import os
import re
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_settings import BaseSettings
import yaml


class ConfigBaseModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class MenuItems(ConfigBaseModel):
    get_help: Optional[str] = None
    report_a_bug: Optional[str] = None
    about: Optional[str] = None


class Playground(ConfigBaseModel):
    auth_master_username: str = "master"
    auth_max_token_expiration_days: Optional[int] = Field(default=None, ge=0)
    api_url: str = "http://localhost:8000"
    home_url: str = "http://localhost:8501"
    page_icon: str = "https://github.com/etalab-ia/albert-api/blob/main/docs/assets/logo.png?raw=true"
    menu_items: MenuItems = MenuItems()
    logo: str = "https://github.com/etalab-ia/albert-api/blob/main/docs/assets/logo.png?raw=true"
    cache_ttl: int = 1800  # 30 minutes
    postgres: dict = {}

    @field_validator("postgres", mode="after")
    def validate_postgres(cls, postgres):
        if postgres.get("url").startswith("postgresql+asyncpg://"):
            logging.warning("PostgreSQL connection must be sync, force sync connection.")
            postgres["url"] = postgres["url"].replace("postgresql+asyncpg", "postgresql")

        return postgres


class ConfigFile(ConfigBaseModel):
    playground: Playground


class Configuration(BaseSettings):
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
        config = ConfigFile(**yaml.safe_load(file_content))

        values.playground = config.playground

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
def get_configuration() -> Configuration:
    return Configuration()


configuration = get_configuration()
