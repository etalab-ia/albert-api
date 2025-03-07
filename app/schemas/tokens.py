import datetime as dt
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class TokenRequest(BaseModel):
    user: str
    token: str
    expires_at: Optional[int] = Field(None, description="Timestamp in seconds")

    @field_validator("token", mode="before")
    def strip(cls, token):
        if isinstance(token, str):
            token = token.strip()
        return token

    @field_validator("expires_at", mode="before")
    def must_be_future(cls, value):
        if value is not None:
            now_timestamp = int(dt.datetime.now(tz=dt.UTC).timestamp())
            if value <= now_timestamp:
                raise ValueError("Wrong timestamp, must be in the future.")
        return value


class Token(BaseModel):
    object: Literal["token"] = "token"
    id: str
    user: str
    token: str
    created_at: int
    updated_at: int


class Tokens(BaseModel):
    object: Literal["list"] = "list"
    data: List[Token]
