from typing import Dict, List, Optional, Union, Literal, Tuple

from pydantic import BaseModel


#cf https://platform.openai.com/docs/api-reference/audio/createTranscription
class AudioTranscriptionRequest(BaseModel):
    model: Optional[str] = "Systran/faster-distil-whisper-large-v3"
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