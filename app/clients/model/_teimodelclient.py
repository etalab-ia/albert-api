from typing import Optional
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


class TeiModelClient(AsyncOpenAI, BaseModelClient):
    ENDPOINT_TABLE = {
        ENDPOINT__AUDIO_TRANSCRIPTIONS: None,
        ENDPOINT__CHAT_COMPLETIONS: None,
        ENDPOINT__COMPLETIONS: None,
        ENDPOINT__EMBEDDINGS: "/v1/embeddings",
        ENDPOINT__MODELS: "/info",
        ENDPOINT__RERANK: "/rerank",
    }

    def __init__(self, model: str, api_url: str, api_key: str, timeout: int) -> None:
        """
        Initialize the TEI model client and check if the model is available.
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

        response = response.json()
        assert self.model == response["model_id"], f"Model not found ({self.model})."

        # set attributes of the model
        self.max_context_length = response.get("max_input_length")

    def _format_request(self, json: Optional[dict] = None, files: Optional[dict] = None, data: Optional[dict] = None) -> dict:
        """
        Format a request to a client model. Overridden base class method to support TEI Reranking.

        Args:
            endpoint(str): The endpoint to forward the request to.
            json(dict): The JSON body to use for the request.
            files(dict): The files to use for the request.
            data(dict): The data to use for the request.

        Returns:
            tuple: The formatted request composed of the url, headers, json, files and data.
        """
        url = urljoin(base=self.api_url, url=self.ENDPOINT_TABLE[self.endpoint])
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if json and "model" in json:
            json["model"] = self.model

        if self.endpoint == ENDPOINT__RERANK:
            json = {"query": json["prompt"], "texts": json["input"]}

        return url, headers, json, files, data
