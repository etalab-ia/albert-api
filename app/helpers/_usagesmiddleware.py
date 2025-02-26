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

        # Get response from next middleware/endpoint
        response = await call_next(request)

        try:
            if endpoint in self.MODELS_ENDPOINTS:
                authorization = request.headers.get("Authorization")
                model = None

                # Extract model from request body if not multipart
                if not content_type.startswith("multipart/form-data"):
                    body = await request.body()
                    body = body.decode(encoding="utf-8")
                    try:
                        model = json.loads(body).get("model") if body else None
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse request body for endpoint {endpoint}")
                        return response

                if authorization:  # Changed this part to match authentication client pattern
                    user_id = AuthenticationClient.api_key_to_user_id(input=authorization)

                    # Extract usage data from response if available
                    usage_data = {}
                    if response.status_code == 200:
                        response_body = await response.body()
                        try:
                            response_json = json.loads(response_body)
                            usage_data = response_json.get("usage", {})
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse response body for endpoint {endpoint}")

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
