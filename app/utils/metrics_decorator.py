import asyncio
from datetime import datetime
import functools
import json
import logging
from typing import Optional

from fastapi import HTTPException, Response
from starlette.responses import StreamingResponse

from app.helpers._streamingresponsewithstatuscode import StreamingResponseWithStatusCode
from app.sql.models import Metrics
from app.sql.session import get_db
# from app.clients.model._basemodelclient import BaseModelClient

logger = logging.getLogger(__name__)


def log_metrics(func):
    """
    Extracts metrics information from the request's response forwarded to the model and logs it to the database.
    It captures the request model name, client url, time to first token, total latency ...
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = datetime.now()
        metrics = Metrics(datetime=start_time, latency=None, time_to_first_token=None)
        logger.error("@@@")
        logger.error(f"metrics: {metrics}")
        logger.error(f"{args}")

        for arg in args:
            logger.error(f"{arg.model}")

        # find the model client object
        # model_client = next((arg for arg in args if isinstance(arg, BaseModelClient)), None)
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
                return extract_metrics_from_streaming_response(response=response, start_time=start_time, metrics=metrics)

            # extract metrics from non-streaming response
            else:
                # extract_metrics_from_response calls perform_log internally
                asyncio.create_task(extract_metrics_from_response(response=response, start_time=start_time, metrics=metrics))
                return response

        except HTTPException as e:
            logger.error(f"Failed to log metrics for model client ({model_client.model} <{model_client.api_url}>): {e}")
            raise e  # Re-raise the exception for FastAPI to handle

    return wrapper


def extract_metrics_from_streaming_response(response: StreamingResponse, start_time: datetime, metrics: Metrics) -> StreamingResponseWithStatusCode:
    original_stream = response.body_iterator
    buffer = []

    async def wrapped_stream():
        nonlocal metrics, buffer
        response_status_code = None

        async for chunk in original_stream:  # This item is (content, status_from_original_stream)
            if isinstance(chunk, tuple):
                content = chunk[0]
                response_status_code = chunk[1]
            else:
                content = chunk
                response_status_code = response.status_code

            try:
                metrics.time_to_first_token = int((datetime.now() - start_time).total_seconds() * 1000) if metrics.time_to_first_token is None else metrics.time_to_first_token  # fmt: off
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

        asyncio.create_task(perform_log(response, metrics, start_time))

    return StreamingResponseWithStatusCode(wrapped_stream(), media_type=response.media_type)


async def extract_metrics_from_response(response: Response, start_time: datetime, metrics: Metrics):
    """
    Extracts metrics information from the response and logs it to the database.
    """

    try:
        body = {}
        if hasattr(response, "body") and response.body:
            body = json.loads(response.body)

        metrics.model = body.get("model", None)
    except Exception as e:
        logger.warning(f"Failed to parse JSON response body: {response.body} ({e})")
        return

    asyncio.create_task(perform_log(response, metrics, start_time))


async def perform_log(response: Optional[Response], metrics: Metrics, start_time: datetime):
    """
    Logs the metrics to the database.
    """

    metrics.latency = int((datetime.now() - start_time).total_seconds() * 1000)

    # if usage.request_model:
    #     usage.request_model = global_context.models.aliases.get(usage.request_model, usage.request_model)

    async for session in get_db():
        session.add(metrics)
        try:
            await session.commit()
        except Exception as e:
            logger.error(f"Failed to log metrics: {e}")
            await session.rollback()
        finally:
            await session.close()
