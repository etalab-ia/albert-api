from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel


class Role(Enum):
    USER = 0
    CLIENT = 1
    ADMIN = 2

    @classmethod
    def get(cls, name: str, default=None) -> Enum | Any:
        try:
            return cls.__getitem__(name=name)
        except KeyError:
            return default


class User(BaseModel):
    id: str
    name: Optional[str] = None
    role: Role
