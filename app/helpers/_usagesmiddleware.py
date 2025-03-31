from datetime import datetime
import json
import traceback
from typing import Callable, Optional

from fastapi import Request, Response
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from app.sql.models import Usage
from app.sql.session import get_db
from app.utils import variables
from app.utils.logging import logger


class UsagesMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, db_func: Callable[[], Session] = get_db):
        super().__init__(app)
        self.db_func = db_func
        # Get all model endpoints from variables.py
        self.MODELS_ENDPOINTS = [getattr(variables, var_name) for var_name in dir(variables) if var_name.startswith("ENDPOINT__")]

    async def _extract_model_from_multipart(self, body: bytes, content_type: str) -> Optional[str]:
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

    async def _extract_model_from_json(self, body: bytes) -> Optional[str]:
        try:
            json_body = json.loads(body.decode("utf-8"))
            return json_body.get("model")
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.warning("Failed to parse JSON request body")
            return None

    async def _handle_streaming_response(self, response: Response) -> tuple[dict, Response]:
        usage_data = {}
        if hasattr(response, "body_iterator"):
            chunks = []
            async for chunk in response.body_iterator:
                chunks.append(chunk)
                try:
                    chunk_data = json.loads(chunk)
                    if "usage" in chunk_data:
                        usage_data = chunk_data["usage"]
                except json.JSONDecodeError:
                    continue

            async def new_body_iterator():
                for chunk in chunks:
                    yield chunk

            response.body_iterator = new_body_iterator()
        return usage_data, response

    async def _log_usage(
        self,
        db: Session,
        start_time: datetime,
        duration: int,
        user_id: int,
        endpoint: str,
        model: str,
        usage_data: dict,
        status: int,
        method: str,
    ):
        try:
            log = Usage(
                datetime=start_time,
                duration=duration,
                user_id=user_id,
                endpoint=endpoint,
                model=model,
                prompt_tokens=usage_data.get("prompt_tokens"),
                completion_tokens=usage_data.get("completion_tokens"),
                total_tokens=usage_data.get("total_tokens"),
                status=status,
                method=method,
            )
            db.add(log)
            db.commit()
        except Exception as e:
            logger.debug(traceback.format_exc())
            logger.error(f"Failed to log usage: {str(e)}")
            db.rollback()
        finally:
            db.close()

    async def dispatch(self, request: Request, call_next) -> Response:
        endpoint = request.url.path
        if not any(endpoint.endswith(model_endpoint) for model_endpoint in self.MODELS_ENDPOINTS):
            return await call_next(request)

        method = request.method
        content_type = request.headers.get("Content-Type", "")
        body = await request.body()

        # Extract model from request
        model = None
        if content_type.startswith("multipart/form-data"):
            model = await self._extract_model_from_multipart(body, content_type)
        else:
            model = await self._extract_model_from_json(body)

        # Preserve original request body
        original_receive = request._receive

        async def receive():
            original = await original_receive()
            return {**original, "body": body}

        request._receive = receive

        start_time = datetime.now()
        # Get response
        response = await call_next(request)
        duration = int((datetime.now() - start_time).total_seconds() * 1000)
        if not model:
            return response

        try:
            from app.utils.exceptions import InvalidAuthenticationSchemeException, InvalidAPIKeyException
            from app.utils.lifespan import context
            from app.utils.settings import settings

            api_key = request.headers.get("Authorization")
            scheme, credentials = api_key.split(sep=" ")
            if scheme != "Bearer":
                raise InvalidAuthenticationSchemeException()

            if not credentials:
                raise InvalidAPIKeyException()

            if credentials == settings.auth.master_key:  # master user can do anything
                logger.info("Skipping usage logging for master user")
                return response

            user_id = await context.iam.check_token(token=credentials)
            if not user_id:
                raise InvalidAPIKeyException()

            if hasattr(request.app.state, "sql"):
                usage_data, response = await self._handle_streaming_response(response)

                # Log usage
                db = next(self.db_func())
                await self._log_usage(
                    db=db,
                    start_time=start_time,
                    duration=duration,
                    user_id=user_id,
                    endpoint=endpoint,
                    model=model,
                    usage_data=usage_data,
                    status=response.status_code,
                    method=method,
                )

        except Exception as e:
            logger.debug(traceback.format_exc())
            logger.error(f"Error in UsagesMiddleware: {str(e)}")

        return response
