from typing import List

from openai.types.audio import Transcription
from pydantic import Field

from app.schemas import BaseModel


class AudioTranscription(Transcription):
    id: str = Field(default=None, description="A unique identifier for the audio transcription.")


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


class AudioTranscriptionVerbose(AudioTranscription):
    language: str
    duration: float
    text: str
    words: List[Word]
    segments: List[Segment]
