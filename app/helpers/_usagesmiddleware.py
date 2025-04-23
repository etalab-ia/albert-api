import asyncio
from datetime import datetime
from typing import Callable, AsyncGenerator

from fastapi import Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware

from app.sql.models import Usage
from app.sql.session import get_db
from app.utils import variables
from app.utils.logging import logger
from app.utils.usage_decorator import NoUserIdException, extract_usage_from_request, extract_usage_from_response

blacklist = [
    variables.ENDPOINT__CHAT_COMPLETIONS,
]


class UsagesMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, db_func: Callable[[], AsyncGenerator[AsyncSession, None]] = get_db):
        super().__init__(app)
        self.db_func = db_func

    async def dispatch(self, request: Request, call_next) -> Response:
        if any(request.url.path.endswith(x) for x in blacklist):
            return await call_next(request)

        start_time = datetime.now()
        usage = Usage(datetime=start_time, endpoint="N/A")
        try:
            await extract_usage_from_request(usage, request)
        except NoUserIdException:
            logger.exception("No user ID found in request, skipping usage logging.")
            return await call_next(request)

        response = await call_next(request)
        asyncio.create_task(extract_usage_from_response(response, start_time, usage))
        return response
