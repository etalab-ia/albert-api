from typing import List, Literal

from fastapi import APIRouter, File, Form, Request, Security, UploadFile
from fastapi.responses import PlainTextResponse

from app.schemas.audio import AudioTranscription
from app.utils.lifespan import models, limiter
from app.utils.security import User, check_api_key, check_rate_limit
from app.utils.settings import settings
from app.utils.variables import ENDPOINT__AUDIO_TRANSCRIPTIONS

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


@router.post(path=ENDPOINT__AUDIO_TRANSCRIPTIONS)
@limiter.limit(limit_value=settings.rate_limit.by_user, key_func=lambda request: check_rate_limit(request=request))
async def audio_transcriptions(
    request: Request,
    file: UploadFile = File(description="The audio file object (not file name) to transcribe, in one of these formats: mp3 or wav."),
    model: str = Form(
        ...,
        description="ID of the model to use. Call `/v1/models` endpoint to get the list of available models, only `automatic-speech-recognition` model type is supported.",
    ),
    language: Literal[*SUPPORTED_LANGUAGES_VALUES] = Form(
        default="fr",
        description="The language of the input audio. Supplying the input language in ISO-639-1 (e.g. en) format will improve accuracy and latency.",
    ),
    prompt: str = Form(default=None, description="Not implemented."),
    response_format: Literal["json", "text"] = Form(
        default="json", description="The format of the transcript output, in one of these formats: `json` or `text`."
    ),
    temperature: float = Form(
        default=0,
        description="The sampling temperature, between 0 and 1. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic. If set to 0, the model will use log probability to automatically increase the temperature until certain thresholds are hit.",
    ),
    timestamp_granularities: List[str] = Form(alias="timestamp_granularities[]", default=["segment"], description="Not implemented."),
    user: User = Security(dependency=check_api_key),
) -> AudioTranscription:
    """
    Transcribes audio into the input language.
    """

    # @TODO: Implement prompt
    # @TODO: Implement timestamp_granularities
    # @TODO: Implement verbose response format

    file_content = await file.read()
    data = {
        "model": model,
        "language": language,
        "response_format": response_format,
        "temperature": temperature,
        "timestamp_granularities": timestamp_granularities,
    }

    model = models.registry[model]
    client = model.get_client(endpoint=ENDPOINT__AUDIO_TRANSCRIPTIONS)
    response = await client.forward_request(method="POST", files={"file": (file.filename, file_content, file.content_type)}, data=data)

    if response_format == "text":
        return PlainTextResponse(content=response.text)

    return AudioTranscription(**response.json())
