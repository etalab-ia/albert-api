from typing import List, Literal

from pydantic import BaseModel, Field


class OCRResponse(BaseModel):
    object: Literal["list"] = "list"
    data: List[dict]


class OCRRequest(BaseModel):
    model: str = Field(
        description="ID of the model to use. Call `/v1/models` endpoint to get the list of available models, only models that support image processing are supported."
    )
    dpi: int = Field(default=150, description="DPI to use for PDF to image conversion")
