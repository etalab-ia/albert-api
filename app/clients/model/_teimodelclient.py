from json import dumps
from typing import Optional
from urllib.parse import urljoin

import httpx
from openai import AsyncOpenAI
import requests
from app.clients.model._basemodelclient import BaseModelClient
from app.utils.variables import (
    ENDPOINT__AUDIO_TRANSCRIPTIONS,
    ENDPOINT__CHAT_COMPLETIONS,
    ENDPOINT__COMPLETIONS,
    ENDPOINT__EMBEDDINGS,
    ENDPOINT__MODELS,
    ENDPOINT__OCR,
    ENDPOINT__RERANK,
)


class TeiModelClient(AsyncOpenAI, BaseModelClient):
    ENDPOINT_TABLE = {
        ENDPOINT__AUDIO_TRANSCRIPTIONS: None,
        ENDPOINT__CHAT_COMPLETIONS: None,
        ENDPOINT__COMPLETIONS: None,
        ENDPOINT__EMBEDDINGS: "/v1/embeddings",
        ENDPOINT__MODELS: "/info",
        ENDPOINT__OCR: None,
        ENDPOINT__RERANK: "/rerank",
    }

    def __init__(self, model: str, api_url: str, api_key: str, timeout: int, *args, **kwargs) -> None:
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

    def _format_response(self, response: httpx.Response) -> httpx.Response:
        if response.status_code == 200 and "data" not in response.json():  # format response for reranking
            response = httpx.Response(status_code=response.status_code, content=dumps({"data": response.json()}))

        return response
