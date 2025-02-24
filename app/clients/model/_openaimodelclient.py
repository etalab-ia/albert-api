from functools import partial
import time
from urllib.parse import urljoin

from openai import AsyncOpenAI
import requests

from app.clients.model._basemodelclient import BaseModelClient
from app.helpers.rerank import LanguageModelRerank
from app.schemas.models import Model, Models
from app.utils.variables import (
    ENDPOINT__AUDIO_TRANSCRIPTIONS,
    ENDPOINT__CHAT_COMPLETIONS,
    ENDPOINT__COMPLETIONS,
    ENDPOINT__EMBEDDINGS,
    ENDPOINT__MODELS,
    ENDPOINT__RERANK,
)


class OpenaiModelClient(AsyncOpenAI, BaseModelClient):
    ENDPOINT_TABLE = {
        ENDPOINT__AUDIO_TRANSCRIPTIONS: "/v1/audio/transcriptions",
        ENDPOINT__CHAT_COMPLETIONS: "/v1/chat/completions",
        ENDPOINT__COMPLETIONS: "/v1/completions",
        ENDPOINT__EMBEDDINGS: "/v1/embeddings",
        ENDPOINT__MODELS: "/v1/models",
        ENDPOINT__RERANK: None,
    }

    def __init__(self, model: str, api_url: str, api_key: str, timeout: int) -> None:
        self.model = model
        self.api_url = api_url
        self.api_key = api_key
        self.timeout = timeout

        super().__init__(base_url=urljoin(base=self.api_url, url="/v1"), api_key=self.api_key, timeout=self.timeout)

        # overwrite OpenAI methods
        self.models.list = partial(_get_models_list, self)
        self.rerank = LanguageModelRerank(client=self)


########### Overwrite OpenAI methods ############


def _get_models_list(self, *args, **kwargs) -> Models:
    """
    Custom method to overwrite OpenAI's list method (self.models.list()) and make it synchronous for initialization.
    """
    url = urljoin(base=str(self.api_url), url=self.ENDPOINT_TABLE[ENDPOINT__MODELS])
    headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else None

    response = requests.get(url=url, headers=headers, timeout=self.timeout)
    assert response.status_code == 200, f"Failed to get models list ({response.status_code})."

    response = response.json()["data"]
    response = [model for model in response if model["id"] == self.model]
    assert len(response) == 1, "Failed to get models list (model not found)."

    response = response[0]

    data = Model(
        id=self.model,
        created=response.get("created", round(time.time())),
        owned_by=response.get("owned_by", ""),
        max_context_length=None,
    )

    return Models(data=[data])
