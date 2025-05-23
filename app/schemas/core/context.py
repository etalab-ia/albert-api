from typing import Any, Optional

from pydantic import BaseModel

from app.schemas.usage import Usage


class GlobalContext(BaseModel):
    tokenizer: Optional[Any] = None
    models: Optional[Any] = None
    iam: Optional[Any] = None
    limiter: Optional[Any] = None
    documents: Optional[Any] = None

    class Config:
        extra = "allow"


class RequestContext(BaseModel):
    method: Optional[str] = None
    path: Optional[str] = None
    client: Optional[str] = None
    usage: Optional[Usage] = None

    class Config:
        extra = "allow"
