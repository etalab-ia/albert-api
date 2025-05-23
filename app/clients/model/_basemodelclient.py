from abc import ABC
import ast
import importlib
from json import dumps, loads, JSONDecodeError
import logging
import re
import traceback
from typing import Any, Dict, Literal, Optional, Type
from urllib.parse import urljoin
from app.utils.context import request_context

from fastapi import HTTPException
import httpx

from app.schemas.core.settings import ModelClientType
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

    def __init__(self, model: str, api_url: str, api_key: str, timeout: int, *args, **kwargs) -> None:
        self.model = model
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

    def _add_usage_in_additional_data(self, additional_data: Dict[str, Any], json: dict, data: dict, stream: bool) -> None:
        """
        Add usage data to the additional data.

        Args:
            additional_data(Dict[str, Any]): The additional data to add usage data to.
            json(dict): The JSON body of the request.
            data(dict): The data of the response.
            stream(bool): Whether the response is a stream.

        Returns:
            Dict[str, Any]: The additional data with usage data.
        """
        from app.utils.lifespan import context

        if self.endpoint in context.tokenizer.USAGE_COMPLETION_ENDPOINTS:
            try:
                updated_additional_data = additional_data
                if "usage" not in updated_additional_data.get("usage", {}):
                    updated_additional_data["usage"] = {}

                if "prompt_tokens" not in additional_data["usage"]:  # to avoid to recompute this value
                    additional_data["usage"]["prompt_tokens"] = context.tokenizer.get_prompt_tokens(endpoint=self.endpoint, body=json)

                updated_additional_data["usage"]["total_tokens"] = updated_additional_data["usage"]["prompt_tokens"]

                if context.tokenizer.USAGE_COMPLETION_ENDPOINTS[self.endpoint]:
                    updated_additional_data["usage"]["completion_tokens"] = context.tokenizer.get_completion_tokens(endpoint=self.endpoint, response=data, stream=stream)  # fmt: off
                    updated_additional_data["usage"]["total_tokens"] = updated_additional_data["usage"].get("prompt_tokens", 0) + updated_additional_data["usage"]["completion_tokens"]  # fmt: off

                additional_data = updated_additional_data

            except Exception as e:
                # reset additional_data to its original value
                logger.warning(f"Failed to compute usage values for endpoint {self.endpoint}: {e}.")

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

            additional_data.update({"model": self.model})
            additional_data = self._add_usage_in_additional_data(additional_data=additional_data, json=json, data=data, stream=False)
            data.update(additional_data)
            request_context.get().setdefault("llm_stats", []).append(additional_data)

            response = httpx.Response(status_code=response.status_code, content=dumps(data))

        return response

    async def forward_request(
        self,
        method: str,
        json: Optional[dict] = None,
        files: Optional[dict] = None,
        data: Optional[dict] = None,
        additional_data: Dict[str, Any] = {},
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

        async with httpx.AsyncClient(timeout=self.timeout) as async_client:
            try:
                response = await async_client.request(method=method, url=url, headers=headers, json=json, files=files, data=data)
            except (httpx.TimeoutException, httpx.ReadTimeout, httpx.ConnectTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as e:
                raise HTTPException(status_code=504, detail="Request timed out, model is too busy.")
            except Exception as e:
                raise HTTPException(status_code=500, detail=type(e).__name__)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError:
                message = loads(response.text)

                # format error message
                if "message" in message:
                    try:
                        message = ast.literal_eval(message["message"])
                    except Exception:
                        message = message["message"]
                raise HTTPException(status_code=response.status_code, detail=message)

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

        content, data = None, dict()
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
                    for choice in content.get("choices", []):
                        index = choice.get("index", 0)
                        delta = choice.get("delta", {})
                        if index not in data:
                            data[index] = ""
                        delta_content = delta.get("content", "")
                        if delta_content:
                            data[index] += delta_content
                except JSONDecodeError as e:
                    logger.debug(f"Failed to decode JSON from streaming response ({e}) on the following chunk: {line}.")

        # error case
        if content is None:
            return None

        # normal case
        extra_chunk = content  # based on last chunk to conserve the chunk structure
        extra_chunk.update({"choices": []})
        additional_data.update({"model": self.model})
        additional_data = self._add_usage_in_additional_data(additional_data=additional_data, json=json, data=data, stream=True)
        extra_chunk.update(additional_data)
        request_context.get().setdefault("llm_stats", []).append(additional_data)

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
                        elif not re.search(b"data: \[DONE\]", chunk):
                            buffer.append(chunk)

                            yield chunk, response.status_code

                        # end of the stream
                        else:
                            match = re.search(b"data: \[DONE\]", chunk)

                            # error case
                            if not match:
                                yield chunk, response.status_code
                                continue

                            # normal case
                            last_chunks = chunk[: match.start()]
                            done_chunk = chunk[match.start() :]
                            buffer.append(last_chunks)

                            extra_chunk = self._format_stream_response(json=json, response=buffer, additional_data=additional_data)

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
