COLLECTION_DISPLAY_ID__INTERNET = "internet"
COLLECTION_TYPE__PUBLIC = "public"
COLLECTION_TYPE__PRIVATE = "private"

DATABASE_TYPE__REDIS = "redis"
DATABASE_TYPE__QDRANT = "qdrant"
DATABASE_TYPE__GRIST = "grist"
DATABASE_TYPE__ELASTIC = "elastic"
DATABASE_TYPE__SQL = "sql"

DEFAULT_APP_NAME = "Albert API"
DEFAULT_TIMEOUT = 300

ENDPOINT__AUDIO_TRANSCRIPTIONS = "/audio/transcriptions"
ENDPOINT__CHAT_COMPLETIONS = "/chat/completions"
ENDPOINT__COMPLETIONS = "/completions"
ENDPOINT__EMBEDDINGS = "/embeddings"
ENDPOINT__MODELS = "/models"
ENDPOINT__RERANK = "/rerank"
ENDPOINT__OCR = "/ocr"

FILE_TYPE__PDF = "application/pdf"
FILE_TYPE__JSON = "application/json"
FILE_TYPE__TXT = "text/plain"
FILE_TYPE__HTML = "text/html"
FILE_TYPE__MD = "text/markdown"

INTERNET_TYPE__BRAVE = "brave"
INTERNET_TYPE__DUCKDUCKGO = "duckduckgo"

MODEL_CLIENT_TYPE__ALBERT = "albert"
MODEL_CLIENT_TYPE__OPENAI = "openai"
MODEL_CLIENT_TYPE__TEI = "tei"
MODEL_CLIENT_TYPE__VLLM = "vllm"

MODEL_TYPE__AUDIO = "automatic-speech-recognition"
MODEL_TYPE__EMBEDDINGS = "text-embeddings-inference"
MODEL_TYPE__LANGUAGE = "text-generation"
MODEL_TYPE__RERANK = "text-classification"

ROUTER_STRATEGY__ROUND_ROBIN = "round_robin"
ROUTER_STRATEGY__SHUFFLE = "shuffle"

SEARCH_TYPE__HYBRID = "hybrid"
SEARCH_TYPE__LEXICAL = "lexical"
SEARCH_TYPE__SEMANTIC = "semantic"

SUPPORTED_MODEL_CLIENT_TYPES__EMBEDDINGS = [MODEL_CLIENT_TYPE__ALBERT, MODEL_CLIENT_TYPE__OPENAI, MODEL_CLIENT_TYPE__TEI]
SUPPORTED_MODEL_CLIENT_TYPES__LANGUAGE = [MODEL_CLIENT_TYPE__ALBERT, MODEL_CLIENT_TYPE__OPENAI, MODEL_CLIENT_TYPE__VLLM]
SUPPORTED_MODEL_CLIENT_TYPES__RERANK = [MODEL_CLIENT_TYPE__ALBERT, MODEL_CLIENT_TYPE__TEI]
SUPPORTED_MODEL_CLIENT_TYPES__AUDIO = [MODEL_CLIENT_TYPE__ALBERT, MODEL_CLIENT_TYPE__OPENAI]

CHUNKERS = ["LangchainRecursiveCharacterTextSplitter", "NoChunker"]
DEFAULT_CHUNKER = "LangchainRecursiveCharacterTextSplitter"  # TODO: rename RecursiveCharacterTextSplitter and remove from variables ?

ROUTER__MODELS = "models"
ROUTER__CHAT = "chat"
ROUTER__COMPLETIONS = "completions"
ROUTER__EMBEDDINGS = "embeddings"
ROUTER__AUDIO = "audio"
ROUTER__RERANK = "rerank"
ROUTER__SEARCH = "search"
ROUTER__COLLECTIONS = "collections"
ROUTER__FILES = "files"
ROUTER__DOCUMENTS = "documents"
ROUTER__CHUNKS = "chunks"
ROUTER__OCR = "ocr"

ROUTERS = [value for name, value in locals().items() if name.startswith("ROUTER__")]
