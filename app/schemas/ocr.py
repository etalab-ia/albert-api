from typing import List, Literal

from pydantic import Field

from app.schemas import BaseModel
from app.schemas.usage import Usage


class OCR(BaseModel):
    object: Literal["ocr"] = "ocr"
    page: int
    text: str


class OCRs(BaseModel):
    object: Literal["list"] = "list"
    data: List[OCR]
    usage: Usage = Field(default=None, description="Usage information for the request.")
