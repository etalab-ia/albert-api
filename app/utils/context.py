from contextvars import ContextVar

from app.schemas.core.context import GlobalContext, RequestContext

global_context: GlobalContext = GlobalContext()
request_context: ContextVar[RequestContext] = ContextVar("request_context", default=RequestContext())
