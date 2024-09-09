import httpx
from typing import Union

from fastapi import APIRouter, Security, HTTPException, UploadFile, File

from app.schemas.audio import AudioTranscriptionRequest, AudioTranscription, AudioTranscriptionVerbose
from app.schemas.config import AUDIO_MODEL_TYPE
from app.utils.security import check_api_key
from app.utils.lifespan import clients
from app.utils.config import LOGGER


router = APIRouter()

#voir https://platform.openai.com/docs/api-reference/audio/createTranscription
@router.post("/audio/transcriptions")
async def audio_transcriptions(
    file: UploadFile = File(...),
    request: AudioTranscriptionRequest = AudioTranscriptionRequest(model="whisper"),
    _: str = Security(check_api_key)
) -> Union[AudioTranscription, AudioTranscriptionVerbose]:
    """
    API de transcription similaire à l'API d'OpenAI.
    """

    client = clients.models[request["model"]]

    if client.type != AUDIO_MODEL_TYPE:
        raise HTTPException(status_code=400, detail="Le modèle n'est pas un modèle audio.")

    url = f"{client.base_url}audio/transcriptions"
    headers = {"Authorization": f"Bearer {client.api_key}"}
    
    with httpx.AsyncClient(timeout=20) as async_client:
        response = await async_client.request(
            method="POST",
            url=url,
            headers=headers,
            files={"file": file.file},
            json=request,
        )
        response.raise_for_status()
   
        data = response.json()
        if request["response_format"] == "verbon_json":
            return AudioTranscriptionVerbose(**data)
        if request["response_format"] == "json":
            return AudioTranscription(**data)
        raise HTTPException(status_code=400, detail="Invalid response format")

#todo: translation (from openai doc)