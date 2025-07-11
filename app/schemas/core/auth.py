from pydantic import BaseModel


class UserModelLimits(BaseModel):
    tpm: int = 0
    tpd: int = 0
    rpm: int = 0
    rpd: int = 0
