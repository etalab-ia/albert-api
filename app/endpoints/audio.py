import httpx
import json
from typing import Union

from fastapi import APIRouter, Security, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.audio import AudioTranscriptionRequest, AudioTranscription, AudioTranscriptionVerbose
from app.utils.security import check_api_key
from app.utils.lifespan import clients
from app.utils.config import LOGGER
from app.tools import *
from app.tools import __all__ as tools_list
from app.schemas.config import AUDIO_MODEL_TYPE

router = APIRouter()


#voir https://platform.openai.com/docs/api-reference/audio/createTranscription
@router.post("/audio/transcriptions")
async def audio_transcriptions(
    request: AudioTranscriptionRequest, user: str = Security(check_api_key)
) -> Union[AudioTranscription, AudioTranscriptionVerbose]:
    """
    Transcription API similar to OpenAI's API.
    """
    request = dict(request)
    client = clients["models"][request["model"]]
    if client.type != AUDIO_MODEL_TYPE:
        raise HTTPException(status_code=400, detail="Le modèle n'est pas un modèle audio.")

    url = f"{client.base_url}audio/transcriptions"
    headers = {"Authorization": f"Bearer {client.api_key}"}
    
    async_client = httpx.AsyncClient(timeout=20)
    response = await async_client.request(
        method="POST",
        url=url,
        headers=headers,
        json=request,
    )
    response.raise_for_status()
    #todo: check if response is json or text
    data = response.json()
    '''
    if request["response_format"] == "verbon_json":
        return AudioTranscriptionVerbose(**data)
    elif request["response_format"] == "json":
        return AudioTranscription(**data)
    else:
        raise HTTPException(status_code=400, detail="Invalid response format")
    '''
    return data

#todo: translation (from openai doc)