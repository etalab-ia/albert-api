COLLECTION_DISPLAY_ID__INTERNET = "internet"

DATABASE_TYPE__ELASTIC = "elastic"
DATABASE_TYPE__GRIST = "grist"
DATABASE_TYPE__QDRANT = "qdrant"
DATABASE_TYPE__REDIS = "redis"
DATABASE_TYPE__SQL = "sql"

DEFAULT_APP_NAME = "Albert API"
ROOT_ROLE = "root"
DEFAULT_TIMEOUT = 300

ENDPOINT__AUDIO_TRANSCRIPTIONS = "/audio/transcriptions"
ENDPOINT__CHAT_COMPLETIONS = "/chat/completions"
ENDPOINT__CHUNKS = "/chunks"
ENDPOINT__COLLECTIONS = "/collections"
ENDPOINT__COMPLETIONS = "/completions"
ENDPOINT__DOCUMENTS = "/documents"
ENDPOINT__EMBEDDINGS = "/embeddings"
ENDPOINT__FILES = "/files"
ENDPOINT__MODELS = "/models"
ENDPOINT__RERANK = "/rerank"
ENDPOINT__ROLES = "/roles"
ENDPOINT__SEARCH = "/search"
ENDPOINT__TOKENS = "/tokens"
ENDPOINT__USERS = "/users"

FILE_TYPE__PDF = "application/pdf"
FILE_TYPE__JSON = "application/json"
FILE_TYPE__TXT = "text/plain"
FILE_TYPE__HTML = "text/html"
FILE_TYPE__MD = "text/markdown"

MODEL_CLIENT_TYPE__ALBERT = "albert"
MODEL_CLIENT_TYPE__OPENAI = "openai"
MODEL_CLIENT_TYPE__TEI = "tei"
MODEL_CLIENT_TYPE__VLLM = "vllm"

SEARCH_TYPE__HYBRID = "hybrid"
SEARCH_TYPE__LEXICAL = "lexical"
SEARCH_TYPE__SEMANTIC = "semantic"

SUPPORTED_MODEL_CLIENT_TYPES__EMBEDDINGS = [MODEL_CLIENT_TYPE__ALBERT, MODEL_CLIENT_TYPE__OPENAI, MODEL_CLIENT_TYPE__TEI]
SUPPORTED_MODEL_CLIENT_TYPES__LANGUAGE = [MODEL_CLIENT_TYPE__ALBERT, MODEL_CLIENT_TYPE__OPENAI, MODEL_CLIENT_TYPE__VLLM]
SUPPORTED_MODEL_CLIENT_TYPES__RERANK = [MODEL_CLIENT_TYPE__ALBERT, MODEL_CLIENT_TYPE__TEI]
SUPPORTED_MODEL_CLIENT_TYPES__AUDIO = [MODEL_CLIENT_TYPE__ALBERT, MODEL_CLIENT_TYPE__OPENAI]

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
