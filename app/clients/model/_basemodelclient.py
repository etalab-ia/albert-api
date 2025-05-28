from abc import ABC
import ast
import importlib
from json import JSONDecodeError, dumps, loads
import logging
import re
import time
import traceback
from typing import Any, Dict, Literal, Optional, Type
from urllib.parse import urljoin

from fastapi import HTTPException
import httpx

from app.schemas.core.models import ModelClientCarbonImpactParams
from app.schemas.core.settings import ModelClientType
from app.schemas.usage import Detail, Usage
from app.utils.context import generate_request_id, global_context, request_context
from app.utils.utils_eco import impact_carbon
from app.utils.variables import (
    ENDPOINT__AUDIO_TRANSCRIPTIONS,
    ENDPOINT__CHAT_COMPLETIONS,
    ENDPOINT__COMPLETIONS,
    ENDPOINT__EMBEDDINGS,
    ENDPOINT__MODELS,
    ENDPOINT__OCR,
    ENDPOINT__RERANK,
)

logger = logging.getLogger(__name__)


# TODO: audrey -- tests unitaires
# TODO: audrey -- historiser le calcul impact_carbon
# TODO: audrey -- est-ce qu'on affiche tout le dictionnaire d'ecologits?


class BaseModelClient(ABC):
    ENDPOINT_TABLE = {
        ENDPOINT__AUDIO_TRANSCRIPTIONS: None,
        ENDPOINT__CHAT_COMPLETIONS: None,
        ENDPOINT__COMPLETIONS: None,
        ENDPOINT__EMBEDDINGS: None,
        ENDPOINT__MODELS: None,
        ENDPOINT__OCR: None,
        ENDPOINT__RERANK: None,
    }

    def __init__(self, model: str, params: ModelClientCarbonImpactParams, api_url: str, api_key: str, timeout: int, *args, **kwargs) -> None:
        self.model = model
        self.params = params
        self.api_url = api_url
        self.api_key = api_key
        self.timeout = timeout
        self.vector_size = None
        self.max_context_length = None

    @staticmethod
    def import_module(type: Literal[ModelClientType.OPENAI, ModelClientType.VLLM, ModelClientType.TEI]) -> "Type[BaseModelClient]":
        """
        Static method to import a subclass of BaseModelClient.

        Args:
            type(str): The type of model client to import.

        Returns:
            Type[BaseModelClient]: The subclass of BaseModelClient.
        """
        module = importlib.import_module(f"app.clients.model._{type.value}modelclient")
        return getattr(module, f"{type.capitalize()}ModelClient")

    def _get_usage(self, json: dict, data: dict, stream: bool) -> Optional[Usage]:
        """
        Get usage data from request and response.

        Args:
            json(dict): The JSON body of the request.
            data(dict): The data of the response.
            stream(bool): Whether the response is a stream.

        Returns:
            Dict[str, Any]: The additional data with usage data.
        """

        usage = None

        if self.endpoint in global_context.tokenizer.USAGE_COMPLETION_ENDPOINTS:
            try:
                usage = request_context.get().usage

                detail_id = data[0].get("id", generate_request_id()) if stream else data.get("id", generate_request_id())
                detail = Detail(id=detail_id, model=self.model)
                detail.prompt_tokens = global_context.tokenizer.get_prompt_tokens(endpoint=self.endpoint, body=json)

                if global_context.tokenizer.USAGE_COMPLETION_ENDPOINTS[self.endpoint]:
                    detail.completion_tokens = global_context.tokenizer.get_completion_tokens(endpoint=self.endpoint, response=data, stream=stream)

                detail.total_tokens = detail.prompt_tokens + detail.completion_tokens

                usage.details.append(detail)
                usage.prompt_tokens += detail.prompt_tokens
                usage.completion_tokens += detail.completion_tokens
                usage.total_tokens += detail.total_tokens

            except Exception as e:
                logger.debug(traceback.format_exc())
                logger.warning(f"Failed to compute usage values for endpoint {self.endpoint}: {e}.")

        return usage

    def _get_additional_data(self, json: dict, data: dict, stream: bool) -> dict:
        """
        Get additional data from request and response.
        """
        usage = self._get_usage(json=json, data=data, stream=stream)
        request_id = usage.details[-1].id if usage and usage.details else generate_request_id()
        additional_data = {"model": self.model, "id": request_id}

        if usage:
            additional_data["usage"] = usage.model_dump()

        return additional_data

    def _format_request(self, json: Optional[dict] = None, files: Optional[dict] = None, data: Optional[dict] = None) -> dict:
        """
        Format a request to a client model. This method can be overridden by a subclass to add additional headers or parameters. This method format the requested endpoint thanks the ENDPOINT_TABLE attribute.

        Args:
            json(dict): The JSON body to use for the request.
            files(dict): The files to use for the request.
            data(dict): The data to use for the request.

        Returns:
            tuple: The formatted request composed of the url, headers, json, files and data.
        """
        # self.endpoint is set by the ModelRouter
        url = urljoin(base=self.api_url, url=self.ENDPOINT_TABLE[self.endpoint])
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if json and "model" in json:
            json["model"] = self.model

        return url, headers, json, files, data

    def _format_response(self, json: dict, response: httpx.Response, additional_data: Dict[str, Any] = {}) -> httpx.Response:
        """
        Format a response from a client model and add usage data and model ID to the response. This method can be overridden by a subclass to add additional headers or parameters.

        Args:
            json(dict): The JSON body of the request to the API.
            response(httpx.Response): The response from the API.
            additional_data(Dict[str, Any]): The additional data to add to the response (default: {}).

        Returns:
            httpx.Response: The formatted response.
        """

        content_type = response.headers.get("Content-Type", "")
        if content_type == "application/json":
            data = response.json()
            data.update(self._get_additional_data(json=json, data=data, stream=False))
            data.update(additional_data)
            response = httpx.Response(status_code=response.status_code, content=dumps(data))

        return response

    async def forward_request(
        self,
        method: str,
        json: Optional[dict] = None,
        files: Optional[dict] = None,
        data: Optional[dict] = None,
        additional_data: Dict[str, Any] = None,
    ) -> httpx.Response:
        """
        Forward a request to a client model and add model name to the response. Optionally, add additional data to the response.

        Args:
            method(str): The method to use for the request.
            json(Optional[dict]): The JSON body to use for the request.
            files(Optional[dict]): The files to use for the request.
            data(Optional[dict]): The data to use for the request.
            additional_data(Dict[str, Any]): The additional data to add to the response (default: {}).

        Returns:
            httpx.Response: The response from the API.
        """

        url, headers, json, files, data = self._format_request(json=json, files=files, data=data)
        if not additional_data:
            additional_data = {}

        async with httpx.AsyncClient(timeout=self.timeout) as async_client:
            try:
                start_time = time.perf_counter()
                response = await async_client.request(method=method, url=url, headers=headers, json=json, files=files, data=data)
                end_time = time.perf_counter()
                inference_time = end_time - start_time
                additional_data["inference_time"] = inference_time
            except (httpx.TimeoutException, httpx.ReadTimeout, httpx.ConnectTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as e:
                raise HTTPException(status_code=504, detail="Request timed out, model is too busy.")
            except Exception as e:
                raise HTTPException(status_code=500, detail=type(e).__name__)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError:
                try:
                    message = loads(response.text)  # format error message
                    if "message" in message:
                        try:
                            message = ast.literal_eval(message["message"])
                        except Exception:
                            message = message["message"]
                except JSONDecodeError:
                    logger.debug(traceback.format_exc())
                    message = response.text
                raise HTTPException(status_code=response.status_code, detail=message)

            # impact carbon
            if json:
                usage = self._get_usage(json=json, data=response.json(), stream=False)
            if json and usage and usage.details and self.params.active and self.params.total:
                detail = usage.details[-1]
                active_params = self.params.active
                total_params = self.params.total
                model_zone = "FRA"
                token_count = detail.total_tokens
                request_latency = additional_data.get("inference_time", 0)
                additional_data["impact_carbon"] = impact_carbon(active_params, total_params, model_zone, token_count, request_latency)

        # add additional data to the response
        response = self._format_response(json=json, response=response, additional_data=additional_data)

        return response

    def _format_stream_response(self, json: dict, response: list, additional_data: Dict[str, Any] = {}) -> tuple:
        """
        Format streaming response data for chat completions.

        Args:
            json(dict):
            response (list): List of response chunks (buffer).
            additional_data (Dict[str, Any]): Additional data to include in the response.

        Returns:
            tuple: (data, extra) where data is the processed raw data and extra is the formatted response.
        """

        content, chunks = None, list()
        for lines in response:
            lines = lines.decode(encoding="utf-8").split(sep="\n\n")
            for line in lines:
                line = line.strip()
                if not line.startswith("data: "):
                    continue
                line = line.removeprefix("data: ")
                if not line:
                    continue
                try:
                    content = loads(line)
                    chunks.append(content)
                except JSONDecodeError as e:
                    logger.debug(f"Failed to decode JSON from streaming response ({e}) on the following chunk: {line}.")

        # error case
        if content is None:
            return None

        # normal case
        extra_chunk = content  # based on last chunk to conserve the chunk structure
        extra_chunk.update({"choices": []})
        extra_chunk.update(self._get_additional_data(json=json, data=chunks, stream=True))
        extra_chunk.update(additional_data)

        return extra_chunk

    async def forward_stream(
        self,
        method: str,
        json: Optional[dict] = None,
        files: Optional[dict] = None,
        data: Optional[dict] = None,
        additional_data: Dict[str, Any] = {},
    ):
        """
        Forward a stream request to a client model and add model name to the response. Optionally, add additional data to the response.

        Args:
            request(Request): The request to forward.
            method(str): The method to use for the request.
            json(Optional[dict]): The JSON body to use for the request.
            files(Optional[dict]): The files to use for the request.
            data(Optional[dict]): The data to use for the request.
            additional_data(Dict[str, Any]): The additional data to add to the response (default: {}).
        """

        url, headers, json, files, data = self._format_request(json=json, files=files, data=data)

        async with httpx.AsyncClient(timeout=self.timeout) as async_client:
            try:
                async with async_client.stream(method=method, url=url, headers=headers, json=json, files=files, data=data) as response:
                    buffer = list()
                    start_time = time.perf_counter()
                    async for chunk in response.aiter_raw():
                        # error case
                        if response.status_code // 100 != 2:
                            chunks = loads(chunk.decode(encoding="utf-8"))
                            if "message" in chunks:
                                try:
                                    chunks["message"] = ast.literal_eval(chunks["message"])
                                except Exception:
                                    pass
                            chunk = dumps(chunks).encode(encoding="utf-8")
                            yield chunk, response.status_code
                        # normal case
                        else:
                            match = re.search(rb"data: \[DONE\]", chunk)
                            if not match:
                                buffer.append(chunk)

                                yield chunk, response.status_code

                            # end of the stream
                            else:
                                last_chunks = chunk[: match.start()]
                                done_chunk = chunk[match.start() :]
                                buffer.append(last_chunks)

                                end_time = time.perf_counter()
                                inference_time = end_time - start_time
                                additional_data["inference_time"] = inference_time

                                extra_chunk = self._format_stream_response(json=json, response=buffer, additional_data=additional_data)

                                # impact carbon
                                usage = self._get_usage(json=json, data=buffer, stream=True)
                                if usage and usage.details and self.params.active and self.params.total:
                                    detail = usage.details[-1]
                                    active_params = self.params.active
                                    total_params = self.params.total
                                    model_zone = "FRA"
                                    token_count = detail.total_tokens
                                    request_latency = additional_data.get("inference_time", 0)
                                    extra_chunk["impact_carbon"] = impact_carbon(
                                        active_params, total_params, model_zone, token_count, request_latency
                                    )

                                # if error case, yield chunk
                                if extra_chunk is None:
                                    yield chunk, response.status_code
                                    continue

                                yield last_chunks, response.status_code
                                yield f"data: {dumps(extra_chunk)}\n\n".encode(), response.status_code
                                yield done_chunk, response.status_code

            except (httpx.TimeoutException, httpx.ReadTimeout, httpx.ConnectTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as e:
                yield dumps({"detail": "Request timed out, model is too busy."}).encode(), 504
            except Exception as e:
                logger.error(traceback.format_exc())
                yield dumps({"detail": type(e).__name__}).encode(), 500
