import json
from datetime import datetime
from typing import Callable

from fastapi import Request, Response
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from app.clients import AuthenticationClient
from app.db.models import Log
from app.db.session import get_db
from app.utils.logging import logger


class UsagesMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, db_func: Callable[[], Session] = get_db):
        super().__init__(app)
        self.db_func = db_func
        self.MODELS_ENDPOINTS = ["/v1/chat/completions", "/v1/completions", "/v1/embeddings", "/v1/audio/transcriptions"]

    async def dispatch(self, request: Request, call_next) -> Response:
        endpoint = request.url.path
        content_type = request.headers.get("Content-Type", "")
        start_time = datetime.utcnow()
        model = None

        # Store request body if needed
        if endpoint in self.MODELS_ENDPOINTS and not content_type.startswith("multipart/form-data"):
            body = await request.body()

            async def receive():
                return {"type": "http.request", "body": body}

            request._receive = receive

            try:
                json_body = json.loads(body.decode("utf-8"))
                model = json_body.get("model")
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse request body for endpoint {endpoint}")

        # Get response from next middleware/endpoint
        response = await call_next(request)

        if not model:
            # Do not log if model is not specified or if json in request was invalid
            return response
        try:
            if endpoint in self.MODELS_ENDPOINTS:
                authorization = request.headers.get("Authorization")

                if authorization:
                    user_id = AuthenticationClient.api_key_to_user_id(input=authorization)
                    usage_data = {}

                    # Handle streaming response
                    if hasattr(response, "body_iterator"):
                        collected_data = b""
                        async for chunk in response.body_iterator:
                            collected_data += chunk
                            try:
                                # Look for the last complete JSON object in the stream
                                if b"data: " in chunk:
                                    json_str = chunk.split(b"data: ")[-1].strip()
                                    if json_str and json_str != b"[DONE]":
                                        chunk_data = json.loads(json_str)
                                        if "usage" in chunk_data:
                                            usage_data = chunk_data["usage"]
                            except json.JSONDecodeError:
                                continue

                    # Use database session from dependency
                    db = next(self.db_func())
                    try:
                        log = Log(
                            datetime=start_time,
                            user=user_id,
                            endpoint=endpoint,
                            model=model,
                            token_per_sec=usage_data.get("tokens_per_second"),
                            inter_token_latency=usage_data.get("inter_token_latency"),
                            req_tokens_nb=usage_data.get("total_tokens"),
                        )
                        db.add(log)
                        db.commit()
                    except Exception as e:
                        logger.error(f"Failed to log usage: {str(e)}")
                        db.rollback()
                    finally:
                        db.close()

        except Exception as e:
            logger.error(f"Error in UsagesMiddleware: {str(e)}")

        return response
