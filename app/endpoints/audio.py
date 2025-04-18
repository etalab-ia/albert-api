from typing import List, Literal

from fastapi import APIRouter, File, Form, Request, Security, UploadFile
from fastapi.responses import PlainTextResponse

from app.helpers import Authorization
from app.schemas.audio import AudioTranscription
from app.utils.lifespan import context
from app.utils.usage_decorator import log_usage
from app.utils.variables import ENDPOINT__AUDIO_TRANSCRIPTIONS, AUDIO_SUPPORTED_LANGUAGES_VALUES

router = APIRouter()

AudioTranscriptionModel = Form(default=..., description="ID of the model to use. Call `/v1/models` endpoint to get the list of available models, only `automatic-speech-recognition` model type is supported.")  # fmt: off
AudioTranscriptionLanguage = Form(default="fr", description="The language of the input audio. Supplying the input language in ISO-639-1 (e.g. en) format will improve accuracy and latency.")  # fmt: off
AudioTranscriptionPrompt = Form(default=None, description="Not implemented.")  # fmt: off
AudioTranscriptionResponseFormat = Form(default="json", description="The format of the transcript output, in one of these formats: `json` or `text`.")  # fmt: off
AudioTranscriptionTemperature = Form(default=0, description="The sampling temperature, between 0 and 1. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic. If set to 0, the model will use log probability to automatically increase the temperature until certain thresholds are hit.")  # fmt: off
AudioTranscriptionTimestampGranularities = Form(default=["segment"], description="Not implemented.")  # fmt: off


@router.post(path=ENDPOINT__AUDIO_TRANSCRIPTIONS, dependencies=[Security(dependency=Authorization())])
@log_usage
async def audio_transcriptions(
    request: Request,
    file: UploadFile = File(description="The audio file object (not file name) to transcribe, in one of these formats: mp3 or wav."),
    model: str = AudioTranscriptionModel,
    language: Literal[*AUDIO_SUPPORTED_LANGUAGES_VALUES] = AudioTranscriptionLanguage,
    prompt: str = AudioTranscriptionPrompt,
    response_format: Literal["json", "text"] = AudioTranscriptionResponseFormat,
    temperature: float = AudioTranscriptionTemperature,
    timestamp_granularities: List[str] = AudioTranscriptionTimestampGranularities,
) -> AudioTranscription:
    """
    Transcribes audio into the input language.
    """

    # @TODO: Implement prompt
    # @TODO: Implement timestamp_granularities
    # @TODO: Implement verbose response format

    file_content = await file.read()
    model = context.models(model=model)
    client = model.get_client(endpoint=ENDPOINT__AUDIO_TRANSCRIPTIONS)
    data = {
        "model": client.model,
        "language": language,
        "response_format": response_format,
        "temperature": temperature,
        "timestamp_granularities": timestamp_granularities,
    }
    response = await client.forward_request(method="POST", files={"file": (file.filename, file_content, file.content_type)}, data=data)

    if response_format == "text":
        return PlainTextResponse(content=response.text)

    return AudioTranscription(**response.json())
