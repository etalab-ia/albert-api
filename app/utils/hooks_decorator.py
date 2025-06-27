import asyncio
from datetime import datetime
import functools
import json
import logging
from typing import Optional

from fastapi import HTTPException, Request, Response
from sqlalchemy import func, select, update
from starlette.responses import StreamingResponse

from app.helpers._streamingresponsewithstatuscode import StreamingResponseWithStatusCode

from app.sql.models import Usage, User
from app.utils.context import global_context, request_context
from app.utils.depends import get_db_dependency
from app.utils.settings import settings

logger = logging.getLogger(__name__)


def hooks(func):
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
            asyncio.create_task(log_usage(response=None, usage=usage, start_time=start_time))
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
                        usage.cost = data["usage"].get("cost", None)
                        usage.kwh_min = data["usage"].get("carbon", {}).get("kWh", {}).get("min", None)
                        usage.kwh_max = data["usage"].get("carbon", {}).get("kWh", {}).get("max", None)
                        usage.kgco2eq_min = data["usage"].get("carbon", {}).get("kgCO2eq", {}).get("min", None)
                        usage.kgco2eq_max = data["usage"].get("carbon", {}).get("kgCO2eq", {}).get("max", None)

        # Set usage.status with the captured status code before calling write_usage
        if response_status_code is not None:
            usage.status = response_status_code

        asyncio.create_task(log_usage(response=response, usage=usage, start_time=start_time))
        asyncio.create_task(update_budget(usage=usage))

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
        response_usage = body.get("usage", {})
        usage.prompt_tokens = response_usage.get("prompt_tokens", None)
        usage.completion_tokens = response_usage.get("completion_tokens", None)
        usage.total_tokens = response_usage.get("total_tokens", None)
        usage.cost = response_usage.get("cost", None)
        usage.kwh_min = response_usage.get("carbon", {}).get("kWh", {}).get("min", None)
        usage.kwh_max = response_usage.get("carbon", {}).get("kWh", {}).get("max", None)
        usage.kgco2eq_min = response_usage.get("carbon", {}).get("kgCO2eq", {}).get("min", None)
        usage.kgco2eq_max = response_usage.get("carbon", {}).get("kgCO2eq", {}).get("max", None)

    except Exception as e:
        logger.warning(f"Failed to parse JSON response body: {response.body} ({e})")
        return

    asyncio.create_task(log_usage(response, usage, start_time))
    asyncio.create_task(update_budget(usage=usage))


async def log_usage(response: Optional[Response], usage: Usage, start_time: datetime):
    """
    Logs the usage information to the database.
    This function captures the duration of the request and sets the status code of the response if available.
    """

    if settings.monitoring.postgres is None or settings.monitoring.postgres.enabled is False:
        return

    usage.duration = int((datetime.now() - start_time).total_seconds() * 1000)

    # Set usage.status based on the response object ONLY if not already set by streaming logic.
    if usage.status is None:
        usage.status = response.status_code if hasattr(response, "status_code") else None

    if usage.request_model:
        usage.request_model = global_context.models.aliases.get(usage.request_model, usage.request_model)

    async for session in get_db_dependency()():
        session.add(usage)
        try:
            await session.commit()
        except Exception as e:
            logger.error(f"Failed to log usage: {e}")
            await session.rollback()
        finally:
            await session.close()


async def update_budget(usage: Usage):
    """
    Updates the budget of the user by decreasing it by the calculated cost.
    Retrieves the current user budget, and decreases it by min(usage.budget, current_budget_value).
    Uses row-level locking to prevent concurrency issues.
    """
    # Check if there's a budget cost to deduct
    if usage.cost is None or usage.cost == 0:
        return

    user_id = usage.user_id
    cost = usage.cost

    if not user_id:
        logger.warning("No user_id found in usage object for budget update")
        return

    # Decrease the user's budget by the calculated cost with proper locking
    async for session in get_db_dependency()():
        try:
            async with session.begin():
                # Use SELECT FOR UPDATE to lock the user row during the transaction. This prevents concurrent modifications to the budget
                select_stmt = select(User.budget).where(User.id == user_id).with_for_update()
                result = await session.execute(select_stmt)
                current_budget = result.scalar_one_or_none()

                if current_budget is None or current_budget == 0:
                    return

                # Calculate the actual cost to deduct (minimum of requested cost and available budget)
                actual_cost = min(cost, current_budget)
                new_budget = round(current_budget - actual_cost, ndigits=6)

                # Update the budget
                update_stmt = update(User).where(User.id == user_id).values(budget=new_budget, updated_at=func.now()).returning(User.budget)

                result = await session.execute(update_stmt)

        except Exception as e:
            logger.exception(f"Failed to update budget for user {user_id}: {e}")
            return None
        finally:
            await session.close()
