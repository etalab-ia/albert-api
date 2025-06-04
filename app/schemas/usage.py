from typing import List, Optional

from pydantic import Field

from app.schemas import BaseModel


class CarbonFootprintUsageKWh(BaseModel):
    min: Optional[float] = Field(default=None, description="Minimum carbon footprint in kWh.")
    max: Optional[float] = Field(default=None, description="Maximum carbon footprint in kWh.")


class CarbonFootprintUsageKgCO2eq(BaseModel):
    min: Optional[float] = Field(default=None, description="Minimum carbon footprint in kgCO2eq (global warming potential).")
    max: Optional[float] = Field(default=None, description="Maximum carbon footprint in kgCO2eq (global warming potential).")


class CarbonFootprintUsage(BaseModel):
    kWh: CarbonFootprintUsageKWh = Field(default_factory=CarbonFootprintUsageKWh)
    kgCO2eq: CarbonFootprintUsageKgCO2eq = Field(default_factory=CarbonFootprintUsageKgCO2eq)


class BaseUsage(BaseModel):
    prompt_tokens: int = Field(default=0, description="Number of prompt tokens (e.g. input tokens).")
    completion_tokens: int = Field(default=0, description="Number of completion tokens (e.g. output tokens).")
    total_tokens: int = Field(default=0, description="Total number of tokens (e.g. input and output tokens).")
    cost: float = Field(default=0.0, description="Total cost of the request.")
    carbon: CarbonFootprintUsage = Field(default_factory=CarbonFootprintUsage)


class Detail(BaseModel):
    id: str
    model: str
    usage: BaseUsage = Field(default_factory=BaseUsage)


class Usage(BaseUsage):
    details: List[Detail] = []
