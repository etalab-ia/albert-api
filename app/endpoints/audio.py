from typing import List

from fastapi import APIRouter, Form, Security, Request, UploadFile, File

from app.schemas.audio import AudioTranscription, AudioTranscriptionVerbose
from app.schemas.config import AUDIO_MODEL_TYPE
from app.utils.config import DEFAULT_RATE_LIMIT
from app.utils.security import check_api_key, check_rate_limit, User
from app.utils.lifespan import clients, limiter
from app.utils.exceptions import ModelNotFoundException


router = APIRouter()


@router.post("/audio/transcriptions")
@limiter.limit(DEFAULT_RATE_LIMIT, key_func=lambda request: check_rate_limit(request=request))
async def audio_transcriptions(
    request: Request,
    file: UploadFile = File(...),
    model: str = Form(...),
    language: str = Form(None),
    prompt: str = Form(None),
    response_format: str = Form("json"),
    temperature: float = Form(0),
    timestamp_granularities: List[str] = Form(alias="timestamp_granularities[]", default=["segment"]),
    user: User = Security(check_api_key),
) -> AudioTranscription | AudioTranscriptionVerbose:
    """
    API de transcription similaire à l'API d'OpenAI.
    """

    client = clients.models[model]

    # @TODO: check if the file is an audio file
    if client.type != AUDIO_MODEL_TYPE:
        raise ModelNotFoundException()

    file_content = await file.read()

    response = await client.audio.transcriptions.create(
        file=(file.filename, file_content, file.content_type),
        model=model,
        language=language,
        prompt=prompt,
        response_format=response_format,
        temperature=temperature,
        timestamp_granularities=timestamp_granularities,
    )
    return response
