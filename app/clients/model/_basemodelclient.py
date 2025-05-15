from abc import ABC
import ast
import importlib
from json import dumps, loads
from typing import Any, Dict, Literal, Optional, Type
from urllib.parse import urljoin
import logging
from fastapi import HTTPException, Request
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

    def _format_request(self, request: Request, json: Optional[dict] = None, files: Optional[dict] = None, data: Optional[dict] = None) -> dict:
        """
        Format a request to a client model. This method can be overridden by a subclass to add additional headers or parameters. This method format the requested endpoint thanks the ENDPOINT_TABLE attribute.

        Args:
            json(dict): The JSON body to use for the request.
            files(dict): The files to use for the request.
            data(dict): The data to use for the request.

        Returns:
            tuple: The formatted request composed of the url, headers, json, files and data.
        """
        url = urljoin(base=self.api_url, url=self.ENDPOINT_TABLE[request.url.path.removeprefix("/v1")])
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if json and "model" in json:
            json["model"] = self.model

        return url, headers, json, files, data

    def _format_response(self, request: Request, response: httpx.Response, additional_data: Dict[str, Any] = {}) -> httpx.Response:
        """
        Format a response from a client model and add usage data and model ID to the response. This method can be overridden by a subclass to add additional headers or parameters.

        Args:
            response(httpx.Response): The response from the API.

        Returns:
            httpx.Response: The formatted response.
        """
        content_type = response.headers.get("Content-Type", "")
        if content_type == "application/json":
            data = response.json()

            if hasattr(request.app.state, "prompt_tokens"):
                data.update({"usage": {"prompt_tokens": request.app.state.prompt_tokens, "total_tokens": request.app.state.prompt_tokens}})

                if request.url.path.endswith(ENDPOINT__CHAT_COMPLETIONS):
                    from app.utils.lifespan import context

                    contents = [choice.get("message", {}).get("content", "") for choice in data.get("choices", [])]
                    completion_tokens = sum([len(context.tokenizer.encode(content)) for content in contents])
                    data["usage"].update({"completion_tokens": completion_tokens})
                    data["usage"].update({"total_tokens": request.app.state.prompt_tokens + completion_tokens})

            data.update({"model": self.model})
            data.update(additional_data)

            response = httpx.Response(status_code=response.status_code, content=dumps(data))

        return response

    async def forward_request(
        self,
        request: Request,
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

        url, headers, json, files, data = self._format_request(request=request, json=json, files=files, data=data)

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
        response = self._format_response(request=request, response=response, additional_data=additional_data)

        return response

    async def forward_stream(
        self,
        request: Request,
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

        url, headers, json, files, data = self._format_request(request=request, json=json, files=files, data=data)

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
                        elif chunk != b"data: [DONE]\n\n":
                            buffer.append(chunk)

                            yield chunk, response.status_code

                        # end of the stream
                        elif buffer:
                            from app.utils.lifespan import context

                            # @TODO: package in a function and add endpoint condition (chat completions)
                            data, extra, contents = None, dict(), dict()
                            for lines in buffer:
                                lines = lines.decode(encoding="utf-8").split(sep="\n\n")
                                for line in lines:
                                    line = line.strip()
                                    if not line.startswith("data: "):
                                        continue
                                    line = line.removeprefix("data: ")
                                    if not line:
                                        continue
                                    try:
                                        data = loads(line)
                                        for choice in data.get("choices", []):
                                            index = choice.get("index", 0)
                                            delta = choice.get("delta", {})
                                            if index not in contents:
                                                contents[index] = ""
                                            content = delta.get("content", "")
                                            if content:
                                                contents[index] += content
                                    except json.JSONDecodeError as e:
                                        logger.debug(f"Failed to decode JSON from streaming response ({e}) on the following chunk: {line}.")

                            # if error case, yield chunk
                            if data is None:
                                yield chunk, response.status_code

                            # normal case
                            extra = data
                            extra.update({"model": self.model})
                            extra.update({"choices": []})
                            extra.update(
                                {
                                    "usage": {
                                        "prompt_tokens": request.app.state.prompt_tokens,
                                        "completion_tokens": 0,
                                        "total_tokens": request.app.state.prompt_tokens,
                                    }
                                }
                            )
                            if contents:
                                try:
                                    completion_tokens = sum([len(context.tokenizer.encode(contents[index])) for index in contents.keys()])
                                    extra["usage"].update({"completion_tokens": completion_tokens})
                                    extra["usage"].update({"total_tokens": request.app.state.prompt_tokens + completion_tokens})
                                except Exception as e:
                                    logger.warning(f"Failed to calculate completion tokens: {e}")

                            extra.update(additional_data)

                            yield f"data: {dumps(extra)}\n\n".encode(), response.status_code
                            yield chunk, response.status_code

            except (httpx.TimeoutException, httpx.ReadTimeout, httpx.ConnectTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as e:
                yield dumps({"detail": "Request timed out, model is too busy."}).encode(), 504
            except Exception as e:
                yield dumps({"detail": type(e).__name__}).encode(), 500
