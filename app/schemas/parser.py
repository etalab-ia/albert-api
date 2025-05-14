from app.schemas import BaseModel
from typing import Dict, Any


class MarkerPDFResponse(BaseModel):
    format: str
    output: str
    images: Dict[str, str]
    metadata: Dict[str, Any]
    success: bool
