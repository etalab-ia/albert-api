from contextvars import ContextVar

request_context: ContextVar[dict] = ContextVar("request_context", default={})
