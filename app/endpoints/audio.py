from typing import List, Literal, Optional, Union

from fastapi import APIRouter, Form, Security, HTTPException, UploadFile, File

from app.schemas.audio import AudioTranscription, AudioTranscriptionVerbose
from app.schemas.config import AUDIO_MODEL_TYPE
from app.utils.security import check_api_key
from app.utils.lifespan import clients


router = APIRouter()


@router.post("/audio/transcriptions")
async def audio_transcriptions(
    file: UploadFile = File(...),
    model: str = Form(...),
    language: Optional[str] = Form(None),
    prompt: Optional[str] = Form(None),
    response_format: Optional[Literal["json", "verbose_json"]] = Form("json"),
    temperature: Optional[float] = Form(0),
    timestamp_granularities: Optional[List[str]] = Form(alias="timestamp_granularities[]", default=["segment"]),
    _: str = Security(check_api_key),
) -> Union[AudioTranscription, AudioTranscriptionVerbose]:
    """
    API de transcription similaire à l'API d'OpenAI.
    """
    client = clients.models[model]

    if client.type != AUDIO_MODEL_TYPE:
        raise HTTPException(status_code=400, detail="Le modèle n'est pas un modèle audio.")

    file_content = await file.read()
    response = await client.audio.transcriptions.create(
        file=("audio.mp3", file_content, file.content_type),
        model=model,
        language=language,
        prompt=prompt,
        response_format=response_format,
        temperature=temperature,
        timestamp_granularities=timestamp_granularities,
    )
    return response
