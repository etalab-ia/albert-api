from typing import Literal, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    cache_ttl: int = 1800  # 30 minutes
    api_url: str = "http://localhost:8080"
    api_key: str = "changeme"
    max_token_expiration_days: int = 60  # days
    documents_embeddings_model: str
    default_chat_model: Optional[str] = None
