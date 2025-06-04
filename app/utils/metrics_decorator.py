import asyncio
from datetime import datetime
import functools
import json
import logging
from typing import Optional

from coredis import ConnectionPool, Redis
from fastapi import HTTPException, Response
from starlette.responses import StreamingResponse

from app.helpers._streamingresponsewithstatuscode import StreamingResponseWithStatusCode
from app.schemas import BaseModel
from app.utils.settings import settings

logger = logging.getLogger(__name__)


class Metric(BaseModel):
    timestamp: datetime
    time_to_first_token: int|None
    model_name: str
    api_url: str


def log_metrics(func):
    """
    Extracts metrics information from the request's response forwarded to the model and logs it to the database.
    It captures the request model name, client url and time to first token
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = datetime.now()
        metrics = Metric(datetime=start_time, time_to_first_token=None)
        logger.error("@@@")
        logger.error(f"metrics: {metrics}")
        logger.error(f"{args}")

        for arg in args:
            logger.error(arg)
            logger.error(f"{arg.model}")

        model_client = args[0]
        if not model_client:
            raise Exception("No model client object found in args")

        metrics.model_name = model_client.model
        metrics.api_url = model_client.api_url

        # extract metrics from response
        response = None  # initialize in case of early exception not from func
        try:
            # call the endpoint
            response = await func(*args, **kwargs)

            # extract metrics from streaming response
            if isinstance(response, StreamingResponse):
                # extract_metrics_from_streaming_response calls perform_log internally
                return extract_metrics_from_streaming_response(response=response, metrics=metrics)

            # extract metrics from non-streaming response
            else:
                # extract_metrics_from_response calls perform_log internally
                asyncio.create_task(extract_metrics_from_response(response=response, start_time=start_time, metrics=metrics))
                return response

        except HTTPException as e:
            logger.error(f"Failed to log metrics for model client ({model_client.model} <{model_client.api_url}>): {e}")
            raise e  # Re-raise the exception for FastAPI to handle

    return wrapper


def extract_metrics_from_streaming_response(response: StreamingResponse, metrics: Metric) -> StreamingResponseWithStatusCode:
    original_stream = response.body_iterator
    buffer = []

    async def wrapped_stream():
        nonlocal metrics, buffer

        async for chunk in original_stream:  # This item is (content, status_from_original_stream)
            if isinstance(chunk, tuple):
                content = chunk[0]
            else:
                content = chunk

            try:
                metrics.time_to_first_token = int((datetime.now() - metrics.timestamp).total_seconds() * 1000) if metrics.time_to_first_token is None else metrics.time_to_first_token  # fmt: off
                buffer.append(content)  # Appends only the content part
            except Exception:
                logger.warning("Failed to process chunk in streaming response for metrics/buffer calculations")
                # Continue to yield the original item even if buffer append fails
                pass

            yield chunk

        if buffer:
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
                        data = json.loads(line)
                    except json.JSONDecodeError as e:
                        logger.debug(f"Failed to decode JSON from streaming response ({e}) on the following chunk: {chunk}.")
                        continue

                    # last chunk overrides previous chunks
                    if data.get("model"):
                        metrics.model_name = data["model"]

        asyncio.create_task(perform_log(response, metrics))

    return StreamingResponseWithStatusCode(wrapped_stream(), media_type=response.media_type)


async def extract_metrics_from_response(response: Response, metrics: Metric):
    """
    Extracts metrics information from the response and logs it to the database.
    """

    try:
        metrics.time_to_first_token = int((datetime.now() - metrics.timestamp).total_seconds() * 1000)
    except Exception as e:
        logger.warning(f"Failed to parse JSON response body: {response.body} ({e})")
        return

    asyncio.create_task(perform_log(response, metrics))


async def perform_log(response: Optional[Response], metrics: Metric):
    """
    Logs the metrics to the database.
    """

    redis = ConnectionPool(**settings.databases.redis.args) if settings.databases.redis else None
    if redis:
        redis_client = Redis(connection_pool=redis)
        try:
            # Tenter de créer la série temporelle
            time_to_first_token_ts_key = f"metrics_ts:time_to_first_token:{metrics.model_name}:{metrics.api_url}"
            await redis_client.timeseries.add(key=time_to_first_token_ts_key, timestamp=metrics.timestamp, value=metrics.time_to_first_token)
        except Exception as e:
            logger.error(f"Erreur lors du log des metriques {time_to_first_token_ts_key} : {e}")
