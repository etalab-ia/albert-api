from json import dumps
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urljoin

from coredis import ConnectionPool
import httpx
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


class TeiModelClient(BaseModelClient):
    ENDPOINT_TABLE = {
        ENDPOINT__AUDIO_TRANSCRIPTIONS: None,
        ENDPOINT__CHAT_COMPLETIONS: None,
        ENDPOINT__COMPLETIONS: None,
        ENDPOINT__EMBEDDINGS: "/v1/embeddings",
        ENDPOINT__MODELS: "/info",
        ENDPOINT__OCR: None,
        ENDPOINT__RERANK: "/rerank",
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
        Initialize the TEI model client and check if the model is available.
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
            *args,
            **kwargs,
        )

        # check if model is available
        url = urljoin(base=str(self.url), url=self.ENDPOINT_TABLE[ENDPOINT__MODELS])

        response = requests.get(url=url, headers=self.headers, timeout=self.timeout)
        assert response.status_code == 200, f"Failed to get models list ({response.status_code})."

        response = response.json()
        assert self.name == response["model_name"], f"Model not found ({self.name})."

        # set attributes of the model
        self.max_context_length = response.get("max_input_length")

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

    def _format_request(
        self, json: Optional[dict] = None, files: Optional[dict] = None, data: Optional[dict] = None
    ) -> Tuple[str, Dict[str, str], Optional[dict], Optional[dict], Optional[dict]]:
        """
        Format a request to a client model. Overridden base class method to support TEI Reranking.

        Args:
            json(dict): The JSON body to use for the request.
            files(dict): The files to use for the request.
            data(dict): The data to use for the request.

        Returns:
            tuple: The formatted request composed of the url, json, files and data.
        """
        # self.endpoint is set by the ModelRouter
        url = urljoin(base=self.url, url=self.ENDPOINT_TABLE[self.endpoint])
        if json and "model" in json:
            json["model"] = self.name

        if self.endpoint.endswith(ENDPOINT__RERANK):
            json = {"query": json["prompt"], "texts": json["input"]}

        return url, json, files, data

    def _format_response(
        self,
        json: dict,
        response: httpx.Response,
        additional_data: Dict[str, Any] = None,
        request_latency: float = 0.0,
    ) -> httpx.Response:
        """
        Format a response from a client model and add usage data and model ID to the response. This method can be overridden by a subclass to add additional headers or parameters.

        Args:
            json(dict): The JSON body of the request to the API.
            response(httpx.Response): The response from the API.
            additional_data(Dict[str, Any]): The additional data to add to the response (default: {}).

        Returns:
            httpx.Response: The formatted response.
        """

        if additional_data is None:
            additional_data = {}

        content_type = response.headers.get("Content-Type", "")
        if content_type == "application/json":
            data = response.json()
            if isinstance(data, list):  # for TEI reranking
                data = {"data": data}
            data.update(self._get_additional_data(json=json, data=data, stream=False, request_latency=request_latency))
            data.update(additional_data)
            response = httpx.Response(status_code=response.status_code, content=dumps(data))

        return response
