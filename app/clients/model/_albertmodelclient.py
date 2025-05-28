from urllib.parse import urljoin

from openai import AsyncOpenAI
import requests

from app.clients.model._basemodelclient import BaseModelClient
from app.schemas.core.models import ModelClientCarbonImpactParams
from app.utils.variables import (
    ENDPOINT__AUDIO_TRANSCRIPTIONS,
    ENDPOINT__CHAT_COMPLETIONS,
    ENDPOINT__COMPLETIONS,
    ENDPOINT__EMBEDDINGS,
    ENDPOINT__MODELS,
    ENDPOINT__OCR,
    ENDPOINT__RERANK,
)


class AlbertModelClient(AsyncOpenAI, BaseModelClient):
    ENDPOINT_TABLE = {
        ENDPOINT__AUDIO_TRANSCRIPTIONS: "/v1/audio/transcriptions",
        ENDPOINT__CHAT_COMPLETIONS: "/v1/chat/completions",
        ENDPOINT__COMPLETIONS: "/v1/completions",
        ENDPOINT__EMBEDDINGS: "/v1/embeddings",
        ENDPOINT__MODELS: "/v1/models",
        ENDPOINT__OCR: "/v1/chat/completions",
        ENDPOINT__RERANK: "/v1/rerank",
    }
#TODO : AUdrey faire idem pour openai / teimodel / vvlm
    def __init__(self, model: str, params: ModelClientCarbonImpactParams, api_url: str, api_key: str, timeout: int, *args, **kwargs) -> None:
        """
        Initialize the OpenAI model client and check if the model is available.
        """
        BaseModelClient.__init__(self, model=model, params=params, api_url=api_url, api_key=api_key, timeout=timeout, *args, **kwargs)

        AsyncOpenAI.__init__(self, base_url=urljoin(base=self.api_url, url="/v1"), api_key=self.api_key, timeout=self.timeout)

        # check if model is available
        url = urljoin(base=str(self.api_url), url=self.ENDPOINT_TABLE[ENDPOINT__MODELS])
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else None

        response = requests.get(url=url, headers=headers, timeout=self.timeout)
        assert response.status_code == 200, f"Failed to get models list ({response.status_code})."

        response = response.json()["data"]
        response = [model for model in response if model["id"] == self.model or self.model in model["aliases"]]
        assert len(response) == 1, "Failed to get models list (model not found)."

        # set attributes of the model
        response = response[0]
        self.max_context_length = response.get("max_context_length")

        # set vector size
        response = requests.post(
            url=urljoin(base=self.api_url, url=self.ENDPOINT_TABLE[ENDPOINT__EMBEDDINGS]),
            headers=headers,
            json={"model": self.model, "input": "hello world"},
            timeout=self.timeout,
        )
        if response.status_code == 200:
            self.vector_size = len(response.json()["data"][0]["embedding"])
        else:
            self.vector_size = None
