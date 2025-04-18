import asyncio
from datetime import datetime
import functools
import json
import logging

from fastapi import Request
from starlette.responses import StreamingResponse

from app.sql.models import Usage
from app.sql.session import get_db
from app.utils.lifespan import context

logger = logging.getLogger(__name__)


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

        response = await func(*args, **kwargs)
        # Find the Request in args or kwargs
        request = next((arg for arg in args if isinstance(arg, Request)), None)
        if not request:
            request = kwargs.pop("request", None)
        if not request:
            raise Exception("No request found in args or kwargs")
        try:
            await extract_usage_from_request(request, usage, **kwargs)
        except NoUserIdException:
            logger.exception("No user ID found in request, skipping usage logging.")
            return response

        if isinstance(response, StreamingResponse):
            return wrap_streaming_response_into_usage_extractor(response, start_time, usage)
        else:
            asyncio.create_task(extract_usage_from_response(response, start_time, usage))
            return response

    return wrapper


async def extract_usage_from_request(request: Request, usage: Usage, **kwargs):
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
    if not usage.user_id:
        raise NoUserIdException("No user ID found in request")
    usage.token_id = getattr(request.app.state, "token_id", None)

    try:
        body = await request.body()
    except Exception as e:
        logger.warning(f"Failed to read request body: {e}")
        return

    async def get_prompt_tokens(body: bytes):
        try:
            json_body = json.loads(body.decode("utf-8"))
            nb_tokens = sum(len(x["content"].split()) for x in json_body.get("messages", []))
            return nb_tokens
        except Exception:
            logger.warning("Failed to parse JSON request body")
            return None

    usage.prompt_tokens = await get_prompt_tokens(body)


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
                pass
            yield chunk

        if buffer:
            body_content = b"".join(buffer).decode("utf-8")
            usage.completion_tokens = len([x for x in body_content.split("\n") if x]) - 1
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
        usage.completion_tokens = len(response.choices[0].message.content.split())
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
    async for session in get_db():
        session.add(usage)
        try:
            await session.commit()
        except Exception as e:
            logger.error(f"Failed to log usage: {e}")
            await session.rollback()
        finally:
            await session.close()
