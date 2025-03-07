from urllib.parse import urljoin

from openai import AsyncOpenAI
import requests

from app.clients.model._basemodelclient import BaseModelClient
from app.utils.variables import (
    ENDPOINT__AUDIO_TRANSCRIPTIONS,
    ENDPOINT__CHAT_COMPLETIONS,
    ENDPOINT__COMPLETIONS,
    ENDPOINT__EMBEDDINGS,
    ENDPOINT__MODELS,
    ENDPOINT__RERANK,
)


class VllmModelClient(AsyncOpenAI, BaseModelClient):
    ENDPOINT_TABLE = {
        ENDPOINT__AUDIO_TRANSCRIPTIONS: None,
        ENDPOINT__CHAT_COMPLETIONS: "/v1/chat/completions",
        ENDPOINT__COMPLETIONS: None,
        ENDPOINT__EMBEDDINGS: None,
        ENDPOINT__MODELS: "/v1/models",
        ENDPOINT__RERANK: None,
    }

    def __init__(self, model: str, api_url: str, api_key: str, timeout: int) -> None:
        """
        Initialize the VLLM model client and check if the model is available.
        """
        self.model = model
        self.api_url = api_url
        self.api_key = api_key
        self.timeout = timeout

        super().__init__(base_url=urljoin(base=self.api_url, url="/v1"), api_key=self.api_key, timeout=self.timeout)

        # check if model is available
        url = urljoin(base=str(self.api_url), url=self.ENDPOINT_TABLE[ENDPOINT__MODELS])
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else None

        response = requests.get(url=url, headers=headers, timeout=self.timeout)
        assert response.status_code == 200, f"Failed to get models list ({response.status_code})."

        response = response.json()["data"]
        response = [model for model in response if model["id"] == self.model]
        assert len(response) == 1, "Failed to get models list (model not found)."

        # set attributes of the model
        response = response[0]
        self.max_context_length = response.get("max_model_len")

        # set vector size
        self.vector_size = None
