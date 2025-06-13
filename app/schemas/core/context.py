from types import SimpleNamespace
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.usage import Usage


class GlobalContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    tokenizer: Optional[Any] = None
    models: Optional[Any] = None
    iam: Optional[Any] = None
    limiter: Optional[Any] = None
    documents: Optional[Any] = None
    parser: Optional[Any] = None
    mcp: Optional[Any] = SimpleNamespace()


class RequestContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    user_id: Optional[str] = None
    role_id: Optional[str] = None
    token_id: Optional[str] = None
    method: Optional[str] = None
    endpoint: Optional[str] = None
    client: Optional[str] = None
    usage: Optional[Usage] = None
