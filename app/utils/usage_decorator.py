import asyncio
from datetime import datetime
import functools
import json
import logging
from typing import Optional
from unittest.mock import AsyncMock

from fastapi import Request
from starlette.responses import StreamingResponse

from app.sql.models import Usage
from app.sql.session import get_db
from app.utils.lifespan import context

logger = logging.getLogger(__name__)


class StreamingRequestException(Exception):
    """
    Exception raised for streaming requests (i.e., requests with stream=True).
    This exception is used to indicate that the request should be handled accordingly.
    """

    pass


class NoUserIdException(Exception):
    pass


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
        usage = Usage(datetime=start_time, endpoint="N/A")

        # Find the Request in args or kwargs
        request = next((arg for arg in args if isinstance(arg, Request)), None)
        if not request:
            request = kwargs.get("request", None)
        if not request:
            raise Exception("No request found in args or kwargs")
        try:
            await extract_usage_from_request(usage, **kwargs)
        except NoUserIdException:
            logger.exception("No user ID found in request, skipping usage logging.")
            return await func(*args, **kwargs)
        except StreamingRequestException:
            logger.debug("Streaming request, OK for decorator to handle.")

        response = await func(*args, **kwargs)
        if isinstance(response, StreamingResponse):
            return wrap_streaming_response_into_usage_extractor(response, start_time, usage)
        else:
            asyncio.create_task(extract_usage_from_response(response, start_time, usage))
            return response

    wrapper.is_log_usage_decorated = True
    return wrapper


def extract_model_from_multipart(body: bytes, content_type: str) -> Optional[str]:
    try:
        # Find the model field in the multipart form data
        parts = body.split(b"\r\n")
        for i, part in enumerate(parts):
            if b'Content-Disposition: form-data; name="model"' in part and i + 2 < len(parts):
                # The value is 2 lines after the Content-Disposition header
                return parts[i + 2].decode("utf-8")
        return None
    except Exception as e:
        logger.warning(f"Error extracting model from multipart data: {str(e)}")
        return None


async def extract_usage_from_request(usage: Usage, request: Request, **kwargs):
    """
    Extracts usage information from the request and sets it in the Usage object.
    This function looks for the request object in the arguments and keyword arguments
    passed to the decorated function.
    It extracts the request method, endpoint, user ID, token ID, model name, and prompt tokens.
    """
    # Set properties from the request
    usage.endpoint = request.url.path
    usage.method = request.method
    user_obj = getattr(request.app.state, "user", None)
    usage.user_id = getattr(user_obj, "id", None) if user_obj else None
    if usage.user_id is None:
        raise NoUserIdException("No user ID found in request")
    usage.token_id = getattr(request.app.state, "token_id", None)

    try:
        body = await request.body()
        request.body = AsyncMock(return_value=body)
    except Exception as e:
        logger.warning(f"Failed to read request body: {e}")
        return

    content_type = request.headers.get("Content-Type", "")
    # Extract model from request
    if content_type.startswith("multipart/form-data"):
        usage.model = extract_model_from_multipart(body, content_type)
    else:
        try:
            json_body = json.loads(body.decode("utf-8"))
            usage.model = json_body.get("model")
        except Exception:
            logger.warning("Failed to parse JSON request body")
            return
        else:
            if "stream" in json_body and json_body["stream"]:
                raise StreamingRequestException("Streaming request")


def wrap_streaming_response_into_usage_extractor(response: StreamingResponse, start_time: datetime, usage: Usage) -> StreamingResponse:
    """
    Wraps the original StreamingResponse to extract usage information from the stream.
    This function captures the first token from the stream and calculates the completion tokens.
    It also logs the usage information to the database.
    """
    original_stream = response.body_iterator
    buffer = []

    async def wrapped_stream():
        nonlocal usage, buffer
        async for chunk in original_stream:
            try:
                if isinstance(chunk, tuple):  # if StreamingResponseWithStatusCode
                    chunk = chunk[0]
                if usage.time_to_first_token is None:
                    usage.time_to_first_token = int((datetime.now() - start_time).total_seconds() * 1000)
                buffer.append(chunk)
            except Exception:
                logger.warning("Failed to process chunk in streaming response")
                pass
            yield chunk

        if buffer:
            body_content = b"".join(buffer).decode("utf-8")
            for line in body_content.split("\n"):
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        if isinstance(data, dict):
                            usage.model = data.get("model", None)
                            break
                    except json.JSONDecodeError:
                        logger.debug("Failed to decode JSON from streaming response")
            asyncio.create_task(perform_log(usage, start_time, response))

    return StreamingResponse(wrapped_stream(), media_type=response.media_type)


async def extract_usage_from_response(response, start_time: datetime, usage: Usage):
    """
    Extracts usage information from the response and logs it to the database.
    This function captures the completion tokens from the response and calculates the duration of the request.
    It also sets the status code of the response if available.
    """
    try:
        usage.model = response.model
    except Exception:
        logger.debug("Error parsing non-streaming response")
    finally:
        asyncio.create_task(perform_log(usage, start_time, response))


async def perform_log(usage: Usage, start_time: datetime, response):
    """
    Logs the usage information to the database.
    This function captures the duration of the request and sets the status code of the response if available.
    """
    usage.duration = int((datetime.now() - start_time).total_seconds() * 1000)
    if usage.prompt_tokens and usage.completion_tokens:
        usage.total_tokens = usage.prompt_tokens + usage.completion_tokens
    usage.status = response.status_code if hasattr(response, "status_code") else None
    if usage.model:
        usage.request_model = context.models.aliases.get(usage.model, usage.model)
    if hasattr(response, "usage"):
        """usage is a special field in vLLM responses"""
        try:
            usage.prompt_tokens = response.usage.prompt_tokens
            usage.completion_tokens = response.usage.completion_tokens
            usage.total_tokens = usage.prompt_tokens + usage.completion_tokens
        except Exception:
            logger.warning("Error parsing usage from response")
    async for session in get_db():
        session.add(usage)
        try:
            await session.commit()
        except Exception as e:
            logger.error(f"Failed to log usage: {e}")
            await session.rollback()
        finally:
            await session.close()
