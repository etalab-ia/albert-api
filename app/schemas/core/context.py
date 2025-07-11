from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.usage import Usage


class GlobalContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    agent_manager: Optional[Any] = None
    document_manager: Optional[Any] = None
    identity_access_manager: Optional[Any] = None
    limiter: Optional[Any] = None
    model_registry: Optional[Any] = None
    parser_manager: Optional[Any] = None
    tokenizer: Optional[Any] = None


class RequestContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    user_id: Optional[int] = None
    role_id: Optional[int] = None
    token_id: Optional[int] = None
    method: Optional[str] = None
    endpoint: Optional[str] = None
    client: Optional[str] = None
    usage: Optional[Usage] = None
