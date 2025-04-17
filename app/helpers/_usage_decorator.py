import asyncio
from datetime import datetime
import functools
import json
import logging
from typing import Optional

from fastapi import Request
from starlette.responses import StreamingResponse

from app.sql.models import Usage
from app.sql.session import get_db

logger = logging.getLogger(__name__)


def log_usage(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = datetime.now()
        user_id = None
        token_id = None
        endpoint = "N/A"
        model = None
        prompt_tokens = None
        completion_tokens = None
        time_to_first_token = None
        request: Optional[Request] = None

        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
        if not request:
            request = kwargs.get("request")

        if request:
            user_id, token_id, endpoint, model, prompt_tokens = await extract_info_from_request(request)

        response = await func(*args, **kwargs)

        async def perform_log():
            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            async for session in get_db():
                log = Usage(
                    datetime=start_time,
                    duration=duration,
                    user_id=user_id,
                    token_id=token_id,
                    endpoint=endpoint,
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens if prompt_tokens and completion_tokens else None,
                    status=response.status_code if hasattr(response, "status_code") else None,
                    method=request.method if request else None,
                )
                session.add(log)
                try:
                    await session.commit()
                except Exception as e:
                    logger.error(f"Failed to log usage: {e}")
                    await session.rollback()
                finally:
                    await session.close()

        # If the response is a StreamingResponse, wrap the body iterator.
        if isinstance(response, StreamingResponse):
            original_stream = response.body_iterator
            buffer = []

            async def wrapped_stream():
                nonlocal time_to_first_token
                nonlocal buffer
                nonlocal completion_tokens
                async for chunk in original_stream:
                    try:
                        if isinstance(chunk, tuple):  # if StreamingResponseWithStatusCode
                            chunk = chunk[0]
                        if time_to_first_token is None:
                            time_to_first_token = datetime.now() - start_time
                            buffer.append(chunk)
                    except Exception:
                        pass
                    yield chunk

                if buffer:
                    body_content = b"".join(buffer).decode("utf-8")
                    completion_tokens = len([x for x in body_content.split("\n") if x]) - 1
                    asyncio.create_task(perform_log())

            return StreamingResponse(wrapped_stream(), media_type=response.media_type)

        # Else if response is a non-streaming Response, try to log usage from its body.
        else:
            try:
                completion_tokens = len(response.choices[0].message.content.split())
            except Exception:
                logger.exception("Error parsing non-streaming response")
            finally:
                asyncio.create_task(perform_log())
            return response

    async def extract_info_from_request(request):
        endpoint = request.url.path
        user_obj = getattr(request.app.state, "user", None)
        if user_obj:
            user_id = getattr(user_obj, "id", None)
        token_id = getattr(request.app.state, "token_id", None)

        try:
            body = await request.body()
        except Exception:
            body = b""

        content_type = request.headers.get("Content-Type", "")

        async def extract_model_from_multipart(body: bytes, content_type: str) -> Optional[str]:
            try:
                parts = body.split(b"\r\n")
                for i, part in enumerate(parts):
                    if b'Content-Disposition: form-data; name="model"' in part and i + 2 < len(parts):
                        return parts[i + 2].decode("utf-8")
                return None
            except Exception as e:
                logger.warning(f"Error extracting model from multipart data: {e}")
                return None

        async def model_tokens_from_json(body: bytes) -> Optional[str]:
            try:
                json_body = json.loads(body.decode("utf-8"))
                nb_tokens = sum(len(x["content"].split()) for x in json_body.get("messages", []))
                return json_body.get("model"), nb_tokens
            except Exception:
                logger.warning("Failed to parse JSON request body")
                return None, None

        if content_type.startswith("multipart/form-data"):
            model = await extract_model_from_multipart(body, content_type)
        else:
            model, prompt_tokens = await model_tokens_from_json(body)
        return user_id, token_id, endpoint, model, prompt_tokens

    return wrapper
