from urllib.parse import urljoin

from coredis import ConnectionPool
import requests

from app.utils.variables import (
    ENDPOINT__AUDIO_TRANSCRIPTIONS,
    ENDPOINT__CHAT_COMPLETIONS,
    ENDPOINT__COMPLETIONS,
    ENDPOINT__EMBEDDINGS,
    ENDPOINT__MODELS,
    ENDPOINT__OCR,
    ENDPOINT__RERANK,
)

from ._basemodelclient import BaseModelClient


class AlbertModelClient(BaseModelClient):
    ENDPOINT_TABLE = {
        ENDPOINT__AUDIO_TRANSCRIPTIONS: "/v1/audio/transcriptions",
        ENDPOINT__CHAT_COMPLETIONS: "/v1/chat/completions",
        ENDPOINT__COMPLETIONS: "/v1/completions",
        ENDPOINT__EMBEDDINGS: "/v1/embeddings",
        ENDPOINT__MODELS: "/v1/models",
        ENDPOINT__OCR: "/v1/chat/completions",
        ENDPOINT__RERANK: "/v1/rerank",
    }

    def __init__(
        self,
        url: str,
        key: str,
        timeout: int,
        model_name: str,
        model_carbon_footprint_zone: str,
        model_carbon_footprint_total_params: int,
        model_carbon_footprint_active_params: int,
        model_cost_prompt_tokens: float,
        model_cost_completion_tokens: float,
        redis: ConnectionPool,
        metrics_retention_ms: int,
        *args,
        **kwargs,
    ) -> None:
        """
        Initialize the Albert model client and check if the model is available.
        """
        super().__init__(
            url=url,
            key=key,
            timeout=timeout,
            model_name=model_name,
            model_carbon_footprint_zone=model_carbon_footprint_zone,
            model_carbon_footprint_total_params=model_carbon_footprint_total_params,
            model_carbon_footprint_active_params=model_carbon_footprint_active_params,
            model_cost_prompt_tokens=model_cost_prompt_tokens,
            model_cost_completion_tokens=model_cost_completion_tokens,
            redis=redis,
            metrics_retention_ms=metrics_retention_ms,
        )

        # check if model is available
        url = urljoin(base=str(self.url), url=self.ENDPOINT_TABLE[ENDPOINT__MODELS])

        response = requests.get(url=url, headers=self.headers, timeout=self.timeout)
        assert response.status_code == 200, f"Failed to get models list ({response.status_code})."

        response = response.json()["data"]
        response = [model for model in response if model["id"] == self.name or self.name in model["aliases"]]
        assert len(response) == 1, f"Model not found ({self.name})."

        # set attributes of the model
        response = response[0]
        self.max_context_length = response.get("max_context_length")

        # set vector size
        response = requests.post(
            url=urljoin(base=self.url, url=self.ENDPOINT_TABLE[ENDPOINT__EMBEDDINGS]),
            headers=self.headers,
            json={"model": self.name, "input": "hello world"},
            timeout=self.timeout,
        )
        if response.status_code == 200:
            self.vector_size = len(response.json()["data"][0]["embedding"])
        else:
            self.vector_size = None
