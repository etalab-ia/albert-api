from app.schemas import BaseModel
from typing import Dict, Any
from app.utils.variables import AUDIO_SUPPORTED_LANGUAGES
from enum import Enum

LANGUAGES = {key.title(): value for key, value in AUDIO_SUPPORTED_LANGUAGES.items()}
LANGUAGES = list(LANGUAGES.keys()) + list(LANGUAGES.values())
LANGUAGES = {str(lang).upper(): str(lang) for lang in sorted(set(LANGUAGES))}

Languages = Enum("Language", LANGUAGES, type=str)


class MarkerPDFResponse(BaseModel):
    format: str
    output: str
    images: Dict[str, str]
    metadata: Dict[str, Any]
    success: bool
