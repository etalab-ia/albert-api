from typing import Any, Literal, Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    cache_ttl: int = 1800  # 30 minutes
    base_url: str = "http://localhost:8080/v1"

    # models
    exclude_models: str
    documents_embeddings_model: str
    summarize_toc_model: str
    summarize_summary_model: str
    default_chat_model: Optional[str] = None

    @model_validator(mode="after")
    def validate_models(cls, values) -> Any:
        values.exclude_models = values.exclude_models.split(",")

        if values.default_chat_model:
            assert values.default_chat_model not in values.exclude_models, "Default chat model is in the exclude models"

        assert values.documents_embeddings_model not in values.exclude_models, "Documents embeddings model is in the exclude models"
        assert values.summarize_toc_model not in values.exclude_models, "Summarize toc model is in the exclude models"
        assert values.summarize_summary_model not in values.exclude_models, "Summarize summary model is in the exclude models"

        return values
