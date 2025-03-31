from pydantic import BaseModel
from enum import Enum


class LimitingStrategy(str, Enum):
    MOVING_WINDOW = "moving_window"
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"


class UserModelLimits(BaseModel):
    tpm: int = 0
    tpd: int = 0
    rpm: int = 0
    rpd: int = 0
