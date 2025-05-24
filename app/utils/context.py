from contextvars import ContextVar
from uuid import uuid4

from app.schemas.core.context import GlobalContext, RequestContext

global_context: GlobalContext = GlobalContext()
request_context: ContextVar[RequestContext] = ContextVar("request_context", default=RequestContext())


def generate_request_id() -> str:
    """
    Get the ID of the request.
    """
    return f"request-{str(uuid4()).replace("-", "")}"
