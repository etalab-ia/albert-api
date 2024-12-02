import json
from typing import List, Literal

from fastapi import APIRouter, File, Form, HTTPException, Request, Security, UploadFile
from fastapi.responses import PlainTextResponse
import httpx

from app.schemas.audio import AudioTranscription
from app.schemas.settings import AUDIO_MODEL_TYPE
from app.utils.exceptions import ModelNotFoundException
from app.utils.lifespan import clients, limiter
from app.utils.security import User, check_api_key, check_rate_limit
from app.utils.settings import settings
from app.utils.variables import DEFAULT_TIMEOUT, SUPPORTED_LANGUAGES

router = APIRouter()
SUPPORTED_LANGUAGES_VALUES = sorted(set(SUPPORTED_LANGUAGES.values())) + sorted(set(SUPPORTED_LANGUAGES.keys()))


@router.post("/audio/transcriptions")
@limiter.limit(settings.default_rate_limit, key_func=lambda request: check_rate_limit(request=request))
async def audio_transcriptions(
    request: Request,
    file: UploadFile = File(...),
    model: str = Form(...),
    language: Literal[*SUPPORTED_LANGUAGES_VALUES] = Form(default="fr"),
    prompt: str = Form(None),
    response_format: Literal["json", "text"] = Form(default="json"),
    temperature: float = Form(0),
    timestamp_granularities: List[str] = Form(alias="timestamp_granularities[]", default=["segment"]),
    user: User = Security(dependency=check_api_key),
) -> AudioTranscription:
    """
    API de transcription similaire à l'API d'OpenAI.
    """
    client = clients.models[model]

    if client.type != AUDIO_MODEL_TYPE:
        raise ModelNotFoundException()

    # @TODO: Implement prompt
    # @TODO: Implement timestamp_granularities
    # @TODO: Implement verbose response format

    file_content = await file.read()

    url = f"{client.base_url}audio/transcriptions"
    headers = {"Authorization": f"Bearer {client.api_key}"}

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as async_client:
            response = await async_client.post(
                url=url,
                headers=headers,
                files={"file": (file.filename, file_content, file.content_type)},
                data={"language": language, "response_format": response_format, "temperature": temperature},
            )
            response.raise_for_status()
            if response_format == "text":
                return PlainTextResponse(content=response.text)

            data = response.json()
            return AudioTranscription(**data)

    except Exception as e:
        raise HTTPException(status_code=e.response.status_code, detail=json.loads(s=e.response.text)["message"])
