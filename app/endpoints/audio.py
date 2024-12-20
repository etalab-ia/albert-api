import json
from typing import List, Literal

from fastapi import APIRouter, File, Form, HTTPException, Request, Security, UploadFile
from fastapi.responses import PlainTextResponse
import httpx

from app.schemas.audio import AudioTranscription
from app.utils.exceptions import ModelNotFoundException
from app.utils.lifespan import clients, limiter
from app.utils.security import User, check_api_key, check_rate_limit
from app.utils.settings import settings
from app.utils.variables import DEFAULT_TIMEOUT, AUDIO_MODEL_TYPE

router = APIRouter()

# Supported language from https://github.com/huggingface/transformers/blob/main/src/transformers/models/whisper/tokenization_whisper.py
SUPPORTED_LANGUAGES = {
    "afrikaans": "af",
    "albanian": "sq",
    "amharic": "am",
    "arabic": "ar",
    "armenian": "hy",
    "assamese": "as",
    "azerbaijani": "az",
    "bashkir": "ba",
    "basque": "eu",
    "belarusian": "be",
    "bengali": "bn",
    "bosnian": "bs",
    "breton": "br",
    "bulgarian": "bg",
    "burmese": "my",
    "cantonese": "yue",
    "castilian": "es",
    "catalan": "ca",
    "chinese": "zh",
    "croatian": "hr",
    "czech": "cs",
    "danish": "da",
    "dutch": "nl",
    "english": "en",
    "estonian": "et",
    "faroese": "fo",
    "finnish": "fi",
    "flemish": "nl",
    "french": "fr",
    "galician": "gl",
    "georgian": "ka",
    "german": "de",
    "greek": "el",
    "gujarati": "gu",
    "haitian": "ht",
    "haitian creole": "ht",
    "hausa": "ha",
    "hawaiian": "haw",
    "hebrew": "he",
    "hindi": "hi",
    "hungarian": "hu",
    "icelandic": "is",
    "indonesian": "id",
    "italian": "it",
    "japanese": "ja",
    "javanese": "jw",
    "kannada": "kn",
    "kazakh": "kk",
    "khmer": "km",
    "korean": "ko",
    "lao": "lo",
    "latin": "la",
    "latvian": "lv",
    "letzeburgesch": "lb",
    "lingala": "ln",
    "lithuanian": "lt",
    "luxembourgish": "lb",
    "macedonian": "mk",
    "malagasy": "mg",
    "malay": "ms",
    "malayalam": "ml",
    "maltese": "mt",
    "mandarin": "zh",
    "maori": "mi",
    "marathi": "mr",
    "moldavian": "ro",
    "moldovan": "ro",
    "mongolian": "mn",
    "myanmar": "my",
    "nepali": "ne",
    "norwegian": "no",
    "nynorsk": "nn",
    "occitan": "oc",
    "panjabi": "pa",
    "pashto": "ps",
    "persian": "fa",
    "polish": "pl",
    "portuguese": "pt",
    "punjabi": "pa",
    "pushto": "ps",
    "romanian": "ro",
    "russian": "ru",
    "sanskrit": "sa",
    "serbian": "sr",
    "shona": "sn",
    "sindhi": "sd",
    "sinhala": "si",
    "sinhalese": "si",
    "slovak": "sk",
    "slovenian": "sl",
    "somali": "so",
    "spanish": "es",
    "sundanese": "su",
    "swahili": "sw",
    "swedish": "sv",
    "tagalog": "tl",
    "tajik": "tg",
    "tamil": "ta",
    "tatar": "tt",
    "telugu": "te",
    "thai": "th",
    "tibetan": "bo",
    "turkish": "tr",
    "turkmen": "tk",
    "ukrainian": "uk",
    "urdu": "ur",
    "uzbek": "uz",
    "valencian": "ca",
    "vietnamese": "vi",
    "welsh": "cy",
    "yiddish": "yi",
    "yoruba": "yo",
}

SUPPORTED_LANGUAGES_VALUES = sorted(set(SUPPORTED_LANGUAGES.values())) + sorted(set(SUPPORTED_LANGUAGES.keys()))


@router.post("/audio/transcriptions")
@limiter.limit(settings.rate_limit.by_key, key_func=lambda request: check_rate_limit(request=request))
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
