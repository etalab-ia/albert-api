from enum import Enum
from typing import List, Literal, Union

from fastapi import Form
from openai.types.audio import Transcription
from pydantic import Field

from app.schemas import BaseModel
from app.utils.variables import SUPPORTED_LANGUAGES

SUPPORTED_LANGUAGES = list(SUPPORTED_LANGUAGES.keys()) + list(SUPPORTED_LANGUAGES.values())
SUPPORTED_LANGUAGES = {str(lang).upper(): str(lang) for lang in sorted(set(SUPPORTED_LANGUAGES))}

AudioTranscriptionLanguage = Enum("AudioTranscriptionLanguage", SUPPORTED_LANGUAGES, type=str)

AudioTranscriptionModelForm: str = Form(default=..., description="ID of the model to use. Call `/v1/models` endpoint to get the list of available models, only `automatic-speech-recognition` model type is supported.")  # fmt: off
AudioTranscriptionLanguageForm: Union[AudioTranscriptionLanguage, Literal[""]] = Form(default="", description="The language of the input audio. Supplying the input language in ISO-639-1 (e.g. en) format will improve accuracy and latency.")  # fmt: off
AudioTranscriptionPromptForm = Form(default=None, description="Not implemented.")  # fmt: off
AudioTranscriptionResponseFormatForm: Literal["json", "text"] = Form(default="json", description="The format of the transcript output, in one of these formats: `json` or `text`.")  # fmt: off
AudioTranscriptionTemperatureForm: float = Form(default=0, ge=0, le=1, description="The sampling temperature, between 0 and 1. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic. If set to 0, the model will use log probability to automatically increase the temperature until certain thresholds are hit.")  # fmt: off
AudioTranscriptionTimestampGranularitiesForm: List[str] = Form(default=["segment"], description="Not implemented.")  # fmt: off


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
