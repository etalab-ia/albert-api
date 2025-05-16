import asyncio
from datetime import datetime
import functools
import json
import logging
from typing import Optional
from unittest.mock import AsyncMock

from fastapi import Request, Response
from starlette.responses import StreamingResponse

from app.helpers import StreamingResponseWithStatusCode
from app.sql.models import Usage
from app.sql.session import get_db
from app.utils.variables import ENDPOINT__CHAT_COMPLETIONS

logger = logging.getLogger(__name__)


class StreamingRequestException(Exception):
    """
    Exception raised for streaming requests (i.e., requests with stream=True).
    This exception is used to indicate that the request should be handled accordingly.
    """

    pass


class NoUserIdException(Exception):
    pass


class MasterUserIdException(Exception):
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

        # find the request object
        request = next((arg for arg in args if isinstance(arg, Request)), None)
        if not request:
            request = kwargs.get("request", None)
        if not request:
            raise Exception("No request found in args or kwargs")

        # extract usage from request
        try:
            await extract_usage_from_request(usage=usage, request=request)
        except NoUserIdException:
            logger.exception("No user ID found in request, skipping usage logging.")
            return await func(*args, **kwargs)
        except MasterUserIdException:
            logger.warning("Master user ID found in request, skipping usage logging.")
            return await func(*args, **kwargs)

        # call the endpoint
        response = await func(*args, **kwargs)

        # extract usage from streaming response
        if isinstance(response, StreamingResponse):
            return extract_usage_from_streaming_response(response=response, start_time=start_time, usage=usage)

        # extract usage from non-streaming response
        else:
            asyncio.create_task(extract_usage_from_response(response=response, start_time=start_time, usage=usage))
            return response

    wrapper.is_log_usage_decorated = True
    return wrapper


def extract_model_from_multipart(body: bytes) -> Optional[str]:
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
    # set properties from the request
    usage.endpoint = request.url.path
    usage.method = request.method
    user = getattr(request.app.state, "user", None)
    usage.user_id = getattr(user, "id", None) if user else None
    if usage.user_id is None:
        raise NoUserIdException("No user ID found in request")
    if usage.user_id == 0:
        raise MasterUserIdException("Master user ID found in request")
    usage.token_id = getattr(request.app.state, "token_id", None)
    usage.prompt_tokens = getattr(request.app.state, "prompt_tokens", None)

    try:
        body = await request.body()
        request.body = AsyncMock(return_value=body)
    except Exception as e:
        logger.warning(f"Failed to read request body: {e}")
        return

    content_type = request.headers.get("Content-Type", "")
    # Extract model from request
    if content_type.startswith("multipart/form-data"):
        usage.request_model = extract_model_from_multipart(body)
    else:
        try:
            json_body = json.loads(body.decode("utf-8"))
            usage.request_model = json_body.get("model")
        except Exception:
            logger.warning("Failed to parse JSON request body")
            return


def extract_usage_from_streaming_response(response: StreamingResponse, start_time: datetime, usage: Usage) -> StreamingResponse:
    """
    Wraps the original StreamingResponse to extract usage information from the stream.
    This function captures the first token from the stream and calculates the completion tokens.
    It also logs the usage information to the database.
    """
    print("########## in extract_usage_from_streaming_response", response.status_code)
    original_stream = response.body_iterator
    buffer = []  # type: ignore
    final_response_status_code = None  # Variable to store the status from the first chunk

    async def wrapped_stream():
        nonlocal usage, buffer, final_response_status_code  # Add final_response_status_code
        first_chunk_processed = False
        async for original_item_from_downstream in original_stream:  # This item is (content, status_from_original_stream)
            content_for_buffer_and_logging = original_item_from_downstream
            current_chunk_status_code_for_this_iteration = response.status_code  # Default, overridden if tuple

            if isinstance(original_item_from_downstream, tuple):
                print("########## in wrapped_stream", original_item_from_downstream)
                content_for_buffer_and_logging = original_item_from_downstream[0]
                current_chunk_status_code_for_this_iteration = original_item_from_downstream[1]

            if not first_chunk_processed:
                final_response_status_code = current_chunk_status_code_for_this_iteration
                first_chunk_processed = True

            try:
                usage.time_to_first_token = int((datetime.now() - start_time).total_seconds() * 1000) if usage.time_to_first_token is None else usage.time_to_first_token  # fmt: off
                buffer.append(content_for_buffer_and_logging)  # Appends only the content part
            except Exception:
                logger.warning("Failed to process chunk in streaming response for usage/buffer calculations")
                # Continue to yield the original item even if buffer append fails
                pass

            # Yield the original item from the downstream iterator.
            # This preserves its structure, e.g., (content, original_status_code),
            # ensuring the correct status code is passed to StreamingResponseWithStatusCode.
            yield original_item_from_downstream

        if buffer:
            from app.utils.lifespan import context

            content = dict()
            body = b"".join(buffer).decode("utf-8").split("\n\n")
            # process each line that starts with "data: " and contains valid JSON
            for chunk in body:  # Renamed 'chunk' to 'chunk_str' to avoid conflict
                # decode and parse chunk_str
                chunk = chunk.strip()
                if not chunk.startswith("data: "):
                    continue
                chunk = chunk.lstrip("data: ")

                # skip empty JSON strings or ending chunk
                if not chunk or chunk == "[DONE]":
                    continue

                # convert chunk_str to dict
                try:
                    data = json.loads(chunk)
                    usage.model = data.get("model", None) if usage.model is None else usage.model

                    if "choices" in data and len(data["choices"]) > 0:
                        choice = data["choices"][0]
                        index = choice.get("index", 0)
                        delta = choice.get("delta", {})

                        # initialize content for this index if it doesn't exist (each index is a different choice)
                        if index not in content:
                            content[index] = ""

                        # append the content from this delta
                        content_part = delta.get("content", "")
                        if content_part:
                            content[index] += content_part

                except json.JSONDecodeError as e:
                    logger.debug(f"Failed to decode JSON from streaming response ({e}) on the following chunk: {chunk}.")

            # calculate completion tokens (sum of all tokens in all choices)
            if content:
                try:
                    usage.completion_tokens = sum([len(context.tokenizer.encode(content[index])) for index in content.keys()])
                except Exception as e:
                    logger.warning(f"Failed to calculate completion tokens: {e}")

        # Set usage.status with the captured status code before calling perform_log
        if final_response_status_code is not None:
            usage.status = final_response_status_code
            # Optional: print(f"########## wrapped_stream: usage.status set to {usage.status}")

        asyncio.create_task(perform_log(response, usage, start_time))

    return StreamingResponseWithStatusCode(wrapped_stream(), media_type=response.media_type)


async def extract_usage_from_response(response: Response, start_time: datetime, usage: Usage):
    """
    Extracts usage information from the response and logs it to the database.
    This function captures the completion tokens from the response and calculates the duration of the request.
    It also sets the status code of the response if available.
    """
    from app.utils.lifespan import context

    body = json.loads(response.body)
    try:
        usage.model = body.get("model", None)
        if usage.endpoint == f"/v1{ENDPOINT__CHAT_COMPLETIONS}":
            # calculate completion tokens (sum of all tokens in all choices)
            contents = [choice.message.content for choice in body.get("choices", [])]
            usage.completion_tokens = sum([len(context.tokenizer.encode(content)) for content in contents])

    except Exception as e:
        logger.debug(f"Error parsing non-streaming response: {e}")
    finally:
        asyncio.create_task(perform_log(response, usage, start_time))


async def perform_log(response: Response, usage: Usage, start_time: datetime):
    """
    Logs the usage information to the database.
    This function captures the duration of the request and sets the status code of the response if available.
    """
    from app.utils.lifespan import context

    usage.duration = int((datetime.now() - start_time).total_seconds() * 1000)

    # Set usage.status based on the response object ONLY if not already set by streaming logic.
    if usage.status is None:
        usage.status = response.status_code if hasattr(response, "status_code") else None

    if usage.request_model:
        usage.request_model = context.models.aliases.get(usage.request_model, usage.request_model)
    if usage.completion_tokens and usage.prompt_tokens:
        usage.total_tokens = usage.prompt_tokens + usage.completion_tokens

    async for session in get_db():
        session.add(usage)
        try:
            await session.commit()
        except Exception as e:
            logger.error(f"Failed to log usage: {e}")
            await session.rollback()
        finally:
            await session.close()
