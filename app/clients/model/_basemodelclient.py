import asyncio
from abc import ABC
import ast
import importlib
from json import JSONDecodeError, dumps, loads
import logging
import re
import time
import traceback
from datetime import datetime
from typing import Any, Dict, Optional, Type
from urllib.parse import urljoin

from coredis import ConnectionPool, Redis
from fastapi import HTTPException
import httpx

from app.schemas.core.settings import ModelClientCarbonFootprint, ModelClientType
from app.schemas.core.metric import Metric
from app.schemas.models import ModelCosts
from app.schemas.usage import Detail, Usage
from app.utils.carbon import get_carbon_footprint
from app.utils.context import generate_request_id, global_context, request_context
from app.utils.variables import (
    ENDPOINT__AUDIO_TRANSCRIPTIONS,
    ENDPOINT__CHAT_COMPLETIONS,
    ENDPOINT__COMPLETIONS,
    ENDPOINT__EMBEDDINGS,
    ENDPOINT__MODELS,
    ENDPOINT__OCR,
    ENDPOINT__RERANK,
)
from app.utils.settings import settings

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

    def __init__(
        self, model: str, costs: ModelCosts, carbon: ModelClientCarbonFootprint, api_url: str, api_key: str, timeout: int, redis_connection: ConnectionPool, *args, **kwargs
    ) -> None:
        self.model = model
        self.costs = costs
        self.carbon = carbon
        self.api_url = api_url
        self.api_key = api_key
        self.timeout = timeout
        self.vector_size = None
        self.max_context_length = None
        self.redis_connection = redis_connection

    @staticmethod
    async def import_module(
            type: ModelClientType,
            redis_connection_pool: ConnectionPool,
            model_name: str,
            api_url: str,
    ) -> "Type[BaseModelClient]":
        """
        Static method to import a subclass of BaseModelClient.

        Args:
            type(str): The type of model client to import.
            redis_connection_pool(ConnectionPool): Connection pool to redis database.
            model_name(str): The name of the model this client gives access to.
            api_url(str): The uri of the API serving this client's model.

        Returns:
            Type[BaseModelClient]: The subclass of BaseModelClient.
        """
        await BaseModelClient.setup_metrics_storage(redis_connection_pool, model_name, api_url)

        module = importlib.import_module(f"app.clients.model._{type.value}modelclient")
        return getattr(module, f"{type.capitalize()}ModelClient")

    @staticmethod
    async def setup_metrics_storage(connection_pool: ConnectionPool, model: str, api_url: str) -> None:
        redis_client = Redis(connection_pool=connection_pool)
        time_to_first_token_ts_key = f"metrics_ts:time_to_first_token:{model}:{api_url}"
        try:
            await redis_client.timeseries.create(key=time_to_first_token_ts_key, retention=settings.general.metrics_retention_ms)
        except Exception as e:
            if str(e) == "TSDB: key already exists":
                logger.debug(f"Redis timeseries {time_to_first_token_ts_key} already exists.")
            else:
                logger.error(f"Creation of redis timeseries {time_to_first_token_ts_key} failed : {e}", exc_info=True)
                await redis_client.reset()

        latency_ts_key = f"metrics_ts:latency:{model}:{api_url}"
        try:
            await redis_client.timeseries.create(key=latency_ts_key, retention=settings.general.metrics_retention_ms)
        except Exception as e:
            if str(e) == "TSDB: key already exists":
                logger.debug(f"Redis timeseries {latency_ts_key} already exists.")
            else:
                logger.error(f"Creation of redis timeseries {latency_ts_key} failed : {e}", exc_info=True)

    def _get_usage(self, json: dict, data: dict, stream: bool, request_latency: float = 0.0) -> Optional[Usage]:
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

                # compute usage for the current (add a detail object)
                detail_id = data[0].get("id", generate_request_id()) if stream else data.get("id", generate_request_id())
                detail = Detail(id=detail_id, model=self.model, usage=Usage())
                detail.usage.prompt_tokens = global_context.tokenizer.get_prompt_tokens(endpoint=self.endpoint, body=json)

                if global_context.tokenizer.USAGE_COMPLETION_ENDPOINTS[self.endpoint]:
                    detail.usage.completion_tokens = global_context.tokenizer.get_completion_tokens(
                        endpoint=self.endpoint,
                        response=data,
                        stream=stream,
                    )

                # @TODO: don't compute carbon if model type is not text-generation or image-text-to-text
                detail.usage.total_tokens = detail.usage.prompt_tokens + detail.usage.completion_tokens
                detail.usage.carbon = get_carbon_footprint(
                    active_params=self.carbon.active_params,
                    total_params=self.carbon.total_params,
                    model_zone=self.carbon.model_zone,
                    token_count=detail.usage.total_tokens,
                    request_latency=request_latency,
                )
                detail.usage.cost = round(detail.usage.prompt_tokens / 1000000 * self.costs.prompt_tokens + detail.usage.completion_tokens / 1000000 * self.costs.completion_tokens, ndigits=6)  # fmt: off
                usage.details.append(detail)

                # add token usage to the total usage
                usage.prompt_tokens += detail.usage.prompt_tokens
                usage.completion_tokens += detail.usage.completion_tokens
                usage.total_tokens += detail.usage.total_tokens

                # add cost to the total usage
                usage.cost += detail.usage.cost

                # add carbon usage to the total usage
                if detail.usage.carbon.kgCO2eq.min is not None:
                    if usage.carbon.kgCO2eq.min is None:
                        usage.carbon.kgCO2eq.min = 0.0
                    usage.carbon.kgCO2eq.min += detail.usage.carbon.kgCO2eq.min
                if detail.usage.carbon.kgCO2eq.max is not None:
                    if usage.carbon.kgCO2eq.max is None:
                        usage.carbon.kgCO2eq.max = 0.0
                    usage.carbon.kgCO2eq.max += detail.usage.carbon.kgCO2eq.max
                if detail.usage.carbon.kWh.min is not None:
                    if usage.carbon.kWh.min is None:
                        usage.carbon.kWh.min = 0.0
                    usage.carbon.kWh.min += detail.usage.carbon.kWh.min
                if detail.usage.carbon.kWh.max is not None:
                    if usage.carbon.kWh.max is None:
                        usage.carbon.kWh.max = 0.0
                    usage.carbon.kWh.max += detail.usage.carbon.kWh.max

            except Exception as e:
                logger.exception(msg=f"Failed to compute usage values for endpoint {self.endpoint}: {e}.")

        return usage

    def _get_additional_data(self, json: dict, data: dict, stream: bool, request_latency: float = 0.0) -> dict:
        """
        Get additional data from request and response.
        """
        usage = self._get_usage(json=json, data=data, stream=stream, request_latency=request_latency)
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

    def _format_response(
        self,
        json: dict,
        response: httpx.Response,
        additional_data: Dict[str, Any] = {},
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

        content_type = response.headers.get("Content-Type", "")
        if content_type == "application/json":
            data = response.json()
            data.update(self._get_additional_data(json=json, data=data, stream=False, request_latency=request_latency))
            data.update(additional_data)
            response = httpx.Response(status_code=response.status_code, content=dumps(data))

        return response

    async def _log_performance_metric(self, metric: Metric) -> None:
        redis_client = Redis(connection_pool=self.redis_connection)
        time_to_first_token_ts_key = f"metrics_ts:time_to_first_token:{metric.model_name}:{metric.api_url}"
        try:
            if metric.time_to_first_token_us is not None:
                await redis_client.timeseries.add(
                    key=time_to_first_token_ts_key, value=metric.time_to_first_token_us, timestamp=metric.timestamp
                )
        except Exception as e:
            logger.error(f"Failed to log request metrics in redis ts {time_to_first_token_ts_key}: {e}", exc_info=True)
            await redis_client.reset()

        latency_ts_key = f"metrics_ts:latency:{metric.model_name}:{metric.api_url}"
        try:
            if metric.latency_ms is not None:
                await redis_client.timeseries.add(key=latency_ts_key, value=metric.latency_ms, timestamp=metric.timestamp)
        except Exception as e:
            logger.error(f"Failed to log request metrics in redis ts {latency_ts_key}: {e}", exc_info=True)

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
            except (httpx.TimeoutException, httpx.ReadTimeout, httpx.ConnectTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as e:
                raise HTTPException(status_code=504, detail="Request timed out, model is too busy.")
            except Exception as e:
                logger.exception(msg=f"Failed to forward request to {self.model}: {e}.")
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

        # add additional data to the response
        request_latency = end_time - start_time
        response = self._format_response(json=json, response=response, additional_data=additional_data, request_latency=request_latency)
        asyncio.create_task(self._log_performance_metric(Metric(
            timestamp=datetime.now(),
            model_name=self.model,
            api_url=self.api_url,
            latency_ms=int(request_latency * 1_000)
        )))

        return response

    def _format_stream_response(
        self,
        json: dict,
        response: list,
        additional_data: Dict[str, Any] = {},
        request_latency: float = 0.0,
    ) -> tuple:
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
        extra_chunk.update(self._get_additional_data(json=json, data=chunks, stream=True, request_latency=request_latency))
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
                    first_token_time = None
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
                                if first_token_time is None:
                                    try:
                                        # The first token comes in the first non-empty chunk of the stream
                                        if loads((chunk.decode(encoding="utf-8")).removeprefix("data: "))["choices"][0]["delta"]["content"] != "":
                                            first_token_time = time.perf_counter()
                                    except Exception as e:
                                        logger.debug("Chunk data could not be processed to compute time to first token")

                                yield chunk, response.status_code

                            # end of the stream
                            else:
                                last_chunks = chunk[: match.start()]
                                done_chunk = chunk[match.start() :]

                                # Edge case: the stream consists in just one group of chunks
                                if first_token_time is None and last_chunks != "" and len(buffer) == 0:
                                    first_token_time = time.perf_counter()

                                buffer.append(last_chunks)

                                end_time = time.perf_counter()
                                request_latency = end_time - start_time
                                if first_token_time is not None:
                                    request_time_to_first_token = first_token_time - start_time
                                else:
                                    logger.warning(f"Time to first token could not be determined for request {request_context.get().id}.")

                                extra_chunk = self._format_stream_response(
                                    json=json,
                                    response=buffer,
                                    additional_data=additional_data,
                                    request_latency=request_latency,
                                )
                                asyncio.create_task(self._log_performance_metric(Metric(
                                    timestamp=datetime.now(),
                                    time_to_first_token_us=int(request_time_to_first_token * 1_000_000) if first_token_time is not None else None,
                                    latency_ms=int(request_latency * 1_000),
                                    model_name=self.model,
                                    api_url=self.api_url,
                                )))

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
