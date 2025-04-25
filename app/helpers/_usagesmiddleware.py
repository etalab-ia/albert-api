import asyncio
from datetime import datetime
from typing import AsyncGenerator, Callable

from fastapi import Request, Response
from fastapi.routing import APIRoute
from starlette.routing import Match

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware

from app.sql.models import Usage
from app.sql.session import get_db
from app.utils.logging import logger
from app.utils.usage_decorator import NoUserIdException, StreamingRequestException, extract_usage_from_request, extract_usage_from_response


class UsagesMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, db_func: Callable[[], AsyncGenerator[AsyncSession, None]] = get_db):
        super().__init__(app)
        self.db_func = db_func

    async def dispatch(self, request: Request, call_next) -> Response:
        route = self.get_route(request)

        if route and getattr(route.endpoint, "is_log_usage_decorated", False):
            logger.debug("Endpoint is decorated with log_usage, skipping middleware logging.")
            return await call_next(request)

        start_time = datetime.now()
        usage = Usage(datetime=start_time, endpoint="N/A")
        try:
            await extract_usage_from_request(usage, request)
        except NoUserIdException:
            logger.info("No user ID found in request, skipping usage logging.")
            return await call_next(request)
        except StreamingRequestException:
            logger.debug("Streaming request, should be handled by decorator.")
            return await call_next(request)

        response = await call_next(request)
        asyncio.create_task(extract_usage_from_response(response, start_time, usage))
        return response

    def get_route(self, request):
        route = None
        for r in request.app.router.routes:
            match, _ = r.matches(request.scope)
            if match == Match.FULL and isinstance(r, APIRoute):
                route = r
                break
        return route
