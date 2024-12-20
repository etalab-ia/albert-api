import json

from fastapi import Request, Response
from prometheus_client import Counter
from starlette.middleware.base import BaseHTTPMiddleware

from app.clients import AuthenticationClient


class MetricsMiddleware(BaseHTTPMiddleware):
    # TODO: add audio endpoint (support for multipart/form-data)
    MODELS_ENDPOINTS = ["/v1/chat/completions", "/v1/completions", "/v1/embeddings"]
    http_requests_by_user = Counter(
        name="http_requests_by_user_and_endpoint",
        documentation="Number of HTTP requests by user and endpoint",
        labelnames=["user", "endpoint", "model"],
    )

    async def dispatch(self, request: Request, call_next) -> Response:
        endpoint = request.url.path
        content_type = request.headers.get("Content-Type", "")

        if endpoint.startswith("/v1"):
            authorization = request.headers.get("Authorization")
            model = None
            if not content_type.startswith("multipart/form-data"):
                body = await request.body()
                body = body.decode(encoding="utf-8")
                try:
                    model = json.loads(body).get("model") if body else None
                except json.JSONDecodeError as e:
                    return Response(
                        status_code=422,
                        content=json.dumps(
                            {
                                "detail": [
                                    {
                                        "type": "json_invalid",
                                        "loc": ["body", e.pos],
                                        "msg": "JSON decode error",
                                        "input": {},
                                        "ctx": {"error": str(e.msg)},
                                    }
                                ]
                            }
                        ),
                        media_type="application/json",
                    )

            if authorization and authorization.startswith("Bearer "):
                user_id = AuthenticationClient.api_key_to_user_id(input=authorization.split(sep=" ")[1])
                self.http_requests_by_user.labels(user=user_id, endpoint=endpoint[3:], model=model).inc()

        response = await call_next(request)

        return response
