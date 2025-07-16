from typing import List, Literal, Union

from fastapi import APIRouter, File, Request, Security, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse

from app.helpers._accesscontroller import AccessController
from app.schemas.audio import (
    AudioTranscription,
    AudioTranscriptionLanguage,
    AudioTranscriptionLanguageForm,
    AudioTranscriptionModelForm,
    AudioTranscriptionPromptForm,
    AudioTranscriptionResponseFormatForm,
    AudioTranscriptionTemperatureForm,
    AudioTranscriptionTimestampGranularitiesForm,
)
from app.utils.context import global_context
from app.utils.variables import ENDPOINT__AUDIO_TRANSCRIPTIONS

router = APIRouter()


@router.post(path=ENDPOINT__AUDIO_TRANSCRIPTIONS, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=AudioTranscription)  # fmt: off
async def audio_transcriptions(
    request: Request,
    file: UploadFile = File(description="The audio file object (not file name) to transcribe, in one of these formats: mp3 or wav."),
    model: str = AudioTranscriptionModelForm,
    language: Union[AudioTranscriptionLanguage, Literal[""]] = AudioTranscriptionLanguageForm,
    prompt: str = AudioTranscriptionPromptForm,
    response_format: Literal["json", "text"] = AudioTranscriptionResponseFormatForm,
    temperature: float = AudioTranscriptionTemperatureForm,
    timestamp_granularities: List[str] = AudioTranscriptionTimestampGranularitiesForm,
) -> JSONResponse | PlainTextResponse:
    """
    Transcribes audio into the input language.
    """

    # @TODO: Implement prompt
    # @TODO: Implement timestamp_granularities
    # @TODO: Implement verbose response format

    file_content = await file.read()

    async def handler(client):
        payload = {
            "model": client.name,
            "response_format": response_format,
            "temperature": temperature,
            "timestamp_granularities": timestamp_granularities,
        }

        if language != "":
            payload["language"] = language.value

        response = await client.forward_request(method="POST",
                                                files={"file": (file.filename, file_content, file.content_type)},
                                                data=payload)

        if response_format == "text":
            return PlainTextResponse(content=response.text)

        return JSONResponse(content=AudioTranscription(**response.json()).model_dump(),
                            status_code=response.status_code)

    model = await global_context.model_registry(model=model)
    return await model.safe_client_access(
        endpoint=ENDPOINT__AUDIO_TRANSCRIPTIONS,
        handler=handler
    )