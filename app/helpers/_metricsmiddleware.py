from prometheus_client import Counter

from app.helpers._authenticationclient import AuthenticationClient
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class MetricsMiddleware(BaseHTTPMiddleware):
    MODELS_ENDPOINTS = ["/v1/chat/completions", "/v1/completions", "/v1/embeddings", "/v1/audio"]

    http_requests_by_user = Counter(
        name="http_requests_by_user_and_endpoint",
        documentation="Number of HTTP requests by user and endpoint",
        labelnames=["user", "endpoint", "model"],
    )

    async def dispatch(self, request: Request, call_next) -> Response:
        endpoint = request.url.path

        if endpoint.startswith("/v1"):
            authorization = request.headers.get("Authorization")
            body = await request.json()
            model = body.get("model") if endpoint in self.MODELS_ENDPOINTS else None

            user_id = AuthenticationClient._api_key_to_user_id(input=authorization.split(" ")[1])

            if authorization and authorization.startswith("Bearer "):
                user_id = AuthenticationClient._api_key_to_user_id(input=authorization.split(" ")[1])
                self.http_requests_by_user.labels(user=user_id, endpoint=endpoint[3:], model=model).inc()

        response = await call_next(request)

        return response
