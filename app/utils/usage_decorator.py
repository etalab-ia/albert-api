import asyncio
from datetime import datetime
import functools
import json
import logging
from typing import Optional

from fastapi import HTTPException, Request, Response
from starlette.responses import StreamingResponse

from app.helpers import StreamingResponseWithStatusCode
from app.sql.models import Usage
from app.sql.session import get_db
from app.utils.context import global_context, request_context

logger = logging.getLogger(__name__)


def log_usage(func):
    """
    Extracts usage information from the request and response and logs it to the database.
    This decorator is designed to be used with FastAPI endpoints.
    It captures the request method, endpoint, user ID, token ID, model name, prompt tokens,
    completion tokens, and the duration of the request.
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = datetime.now()
        usage = Usage(datetime=start_time, endpoint="N/A", model=None, prompt_tokens=None, completion_tokens=None, total_tokens=None)

        # get the request context
        context = request_context.get()
        if context.user_id is None:
            logger.info(f"No user ID found in request, skipping usage logging ({context.endpoint}).")
            return await func(*args, **kwargs)
        if context.user_id == 0:
            logger.info(f"Master user ID found in request, skipping usage logging ({context.endpoint}).")
            return await func(*args, **kwargs)

        usage.user_id = context.user_id
        usage.token_id = context.token_id
        usage.endpoint = context.endpoint
        usage.method = context.method

        # find the request object
        request = next((arg for arg in args if isinstance(arg, Request)), None)
        if not request:
            request = kwargs.get("request", None)
        if not request:
            raise Exception("No request found in args or kwargs")

        # extract usage from request
        await extract_usage_from_request(usage=usage, request=request)

        # extract usage from response
        response = None  # initialize in case of early exception not from func
        try:
            # call the endpoint
            response = await func(*args, **kwargs)

            # extract usage from streaming response
            if isinstance(response, StreamingResponse):
                # extract_usage_from_streaming_response calls perform_log internally
                return extract_usage_from_streaming_response(response=response, start_time=start_time, usage=usage)

            # extract usage from non-streaming response
            else:
                # extract_usage_from_response calls perform_log internally
                asyncio.create_task(extract_usage_from_response(response=response, start_time=start_time, usage=usage))
                return response

        except HTTPException as e:
            usage.status = e.status_code
            # Pass response=None as there isn't a full FastAPI Response object.
            # perform_log will use usage.status which we've just set.
            asyncio.create_task(perform_log(response=None, usage=usage, start_time=start_time))
            raise e  # Re-raise the exception for FastAPI to handle

    return wrapper


async def extract_usage_from_request(usage: Usage, request: Request):
    content_type = request.headers.get("Content-Type", "")

    if content_type.startswith("multipart/form-data"):
        body = await request.form()
        body = {key: value for key, value in body.items()}
        usage.request_model = body.get("model")
    else:
        try:
            body = await request.body()
            body = json.loads(body.decode("utf-8")) if body else {}
            usage.request_model = body.get("model")
        except Exception as e:
            logger.warning(f"Failed to parse JSON request body ({request.url.path}): {e}")


def extract_usage_from_streaming_response(response: StreamingResponse, start_time: datetime, usage: Usage) -> StreamingResponseWithStatusCode:
    original_stream = response.body_iterator
    buffer = []

    async def wrapped_stream():
        nonlocal usage, buffer  # Add final_response_status_code
        response_status_code = None

        async for chunk in original_stream:  # This item is (content, status_from_original_stream)
            if isinstance(chunk, tuple):
                content = chunk[0]
                response_status_code = chunk[1]
            else:
                content = chunk
                response_status_code = response.status_code

            try:
                usage.time_to_first_token = int((datetime.now() - start_time).total_seconds() * 1000) if usage.time_to_first_token is None else usage.time_to_first_token  # fmt: off
                buffer.append(content)  # Appends only the content part
            except Exception:
                logger.warning("Failed to process chunk in streaming response for usage/buffer calculations")
                # Continue to yield the original item even if buffer append fails
                pass

            # Yield the original item from the downstream iterator.
            # This preserves its structure, e.g., (content, original_status_code),
            # ensuring the correct status code is passed to StreamingResponseWithStatusCode.
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
                        usage.model = data["model"]
                    if data.get("usage"):
                        usage.prompt_tokens = data["usage"]["prompt_tokens"]
                        usage.completion_tokens = data["usage"]["completion_tokens"]
                        usage.total_tokens = data["usage"]["total_tokens"]

        # Set usage.status with the captured status code before calling perform_log
        if response_status_code is not None:
            usage.status = response_status_code

        asyncio.create_task(perform_log(response, usage, start_time))

    return StreamingResponseWithStatusCode(wrapped_stream(), media_type=response.media_type)


async def extract_usage_from_response(response: Response, start_time: datetime, usage: Usage):
    """
    Extracts usage information from the response and logs it to the database.
    This function captures the completion tokens from the response and calculates the duration of the request.
    It also sets the status code of the response if available.
    """

    try:
        body = {}
        if hasattr(response, "body") and response.body:
            body = json.loads(response.body)

        usage.model = body.get("model", None)
        usage.prompt_tokens = body.get("usage", {}).get("prompt_tokens", None)
        usage.completion_tokens = body.get("usage", {}).get("completion_tokens", None)
        usage.total_tokens = body.get("usage", {}).get("total_tokens", None)
    except Exception as e:
        logger.warning(f"Failed to parse JSON response body: {response.body} ({e})")
        return

    asyncio.create_task(perform_log(response, usage, start_time))


async def perform_log(response: Optional[Response], usage: Usage, start_time: datetime):
    """
    Logs the usage information to the database.
    This function captures the duration of the request and sets the status code of the response if available.
    """

    usage.duration = int((datetime.now() - start_time).total_seconds() * 1000)

    # Set usage.status based on the response object ONLY if not already set by streaming logic.
    if usage.status is None:
        usage.status = response.status_code if hasattr(response, "status_code") else None

    if usage.request_model:
        usage.request_model = global_context.models.aliases.get(usage.request_model, usage.request_model)

    async for session in get_db():
        session.add(usage)
        try:
            await session.commit()
        except Exception as e:
            logger.error(f"Failed to log usage: {e}")
            await session.rollback()
        finally:
            await session.close()