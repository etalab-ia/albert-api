from typing import List, Literal

from pydantic import BaseModel


class OCRResponse(BaseModel):
    object: Literal["list"] = "list"
    data: List[dict]
