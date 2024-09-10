from typing import Dict, List, Optional, Union, Literal, Tuple

from pydantic import BaseModel, Field
from fastapi import UploadFile, File

'''
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletion,
    ChatCompletionToolChoiceOptionParam,
    ChatCompletionToolParam,
    ChatCompletionChunk,
)
'''

from app.schemas.tools import ToolOutput

#cf https://platform.openai.com/docs/api-reference/audio/createTranscription
class AudioTranscriptionRequest(BaseModel):
    model: Optional[str] = None
    language: Optional[str] = None
    prompt: Optional[str] = None
    response_format: Optional[str] = "json"
    temperature: Optional[float] = 0
    timestamp: Optional[bool] = False

class AudioTranscription(BaseModel):
    text: str

class Word(BaseModel):
    word: str
    start: float
    end: float

class Segment(BaseModel):
    id: int
    seek: int
    start: float
    end: float
    text: str
    tokens: List[int]
    temperature: float
    avg_logprob: float
    compression_ratio: float
    no_speech_prob: float

class AudioTranscriptionVerbose(BaseModel):
    language: str
    duration: float
    text: str
    words: List[Word]
    segments: List[Segment]