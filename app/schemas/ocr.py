from typing import List, Literal

from app.schemas import BaseModel


class OCR(BaseModel):
    object: Literal["ocr"] = "ocr"
    page: int
    text: str


class OCRs(BaseModel):
    object: Literal["list"] = "list"
    data: List[OCR]
