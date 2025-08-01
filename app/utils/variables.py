DEFAULT_APP_NAME = "Albert API"
DEFAULT_TIMEOUT = 300

ENDPOINT__AGENTS_COMPLETIONS = "/agents/completions"
ENDPOINT__AGENTS_TOOLS = "/agents/tools"
ENDPOINT__AUDIO_TRANSCRIPTIONS = "/audio/transcriptions"
ENDPOINT__CHAT_COMPLETIONS = "/chat/completions"
ENDPOINT__CHUNKS = "/chunks"
ENDPOINT__COLLECTIONS = "/collections"
ENDPOINT__COMPLETIONS = "/completions"
ENDPOINT__DOCUMENTS = "/documents"
ENDPOINT__EMBEDDINGS = "/embeddings"
ENDPOINT__FILES = "/files"
ENDPOINT__MODELS = "/models"
ENDPOINT__OCR = "/ocr-beta"
ENDPOINT__PARSE = "/parse-beta"
ENDPOINT__RERANK = "/rerank"
ENDPOINT__ROLES = "/roles"
ENDPOINT__ROLES_ME = "/roles/me"
ENDPOINT__SEARCH = "/search"
ENDPOINT__TOKENS = "/tokens"
ENDPOINT__USERS = "/users"
ENDPOINT__USERS_ME = "/users/me"
ENDPOINT__USAGE = "/usage"


ENDPOINTS = [value for name, value in locals().items() if name.startswith("ENDPOINT__")]

ROUTER__AGENTS = "agents"
ROUTER__AUDIO = "audio"
ROUTER__AUTH = "auth"
ROUTER__CHAT = "chat"
ROUTER__CHUNKS = "chunks"
ROUTER__COLLECTIONS = "collections"
ROUTER__COMPLETIONS = "completions"
ROUTER__DOCUMENTS = "documents"
ROUTER__EMBEDDINGS = "embeddings"
ROUTER__FILES = "files"
ROUTER__MODELS = "models"
ROUTER__MONITORING = "monitoring"
ROUTER__OCR = "ocr"
ROUTER__PARSE = "parse"
ROUTER__RERANK = "rerank"
ROUTER__SEARCH = "search"
ROUTER__USAGE = "usage"
ROUTER__USERS = "users"
ROUTER__MULTIAGENTS = "multiagents"
ROUTER__OAUTH2 = "oauth2"


ROUTERS = [value for name, value in locals().items() if name.startswith("ROUTER__")]

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
