from typing import List

from pydantic import Field

from app.schemas import BaseModel


class CarbonFootprintUsageKwh(BaseModel):
    min: float = 0.0
    max: float = 0.0


class CarbonFootprintUsageKgCO2eq(BaseModel):
    min: float = 0.0
    max: float = 0.0


class CarbonFootprintUsage(BaseModel):
    kwh: CarbonFootprintUsageKwh = Field(default_factory=CarbonFootprintUsageKwh)
    kgCO2eq: CarbonFootprintUsageKgCO2eq = Field(default_factory=CarbonFootprintUsageKgCO2eq)


class BaseUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    carbon: CarbonFootprintUsage = Field(default_factory=CarbonFootprintUsage)


class Detail(BaseModel):
    id: str
    model: str
    usage: BaseUsage = Field(default_factory=BaseUsage)


class Usage(BaseUsage):
    details: List[Detail] = []
