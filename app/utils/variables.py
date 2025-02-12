DEFAULT_APP_NAME = "Albert API"
DEFAULT_TIMEOUT = 300

COLLECTION_DISPLAY_ID__INTERNET = "internet"
COLLECTION_TYPE__PUBLIC = "public"
COLLECTION_TYPE__PRIVATE = "private"

INTERNET_TYPE__BRAVE = "brave"
INTERNET_TYPE__DUCKDUCKGO = "duckduckgo"

DATABASE_TYPE__REDIS = "redis"
DATABASE_TYPE__QDRANT = "qdrant"
DATABASE_TYPE__GRIST = "grist"
DATABASE_TYPE__ELASTIC = "elastic"

SEARCH_TYPE__HYBRID = "hybrid"
SEARCH_TYPE__LEXICAL = "lexical"
SEARCH_TYPE__SEMANTIC = "semantic"

MODEL_TYPE__AUDIO = "automatic-speech-recognition"
MODEL_TYPE__EMBEDDINGS = "text-embeddings-inference"
MODEL_TYPE__LANGUAGE = "text-generation"
MODEL_TYPE__RERANK = "text-classification"

MODEL_CLIENT_TYPE__VLLM = "vllm"
MODEL_CLIENT_TYPE__TEI = "tei"
MODEL_CLIENT_TYPE__OPENAI = "openai"

SUPPORTED_MODEL_CLIENT_TYPES__EMBEDDINGS = [MODEL_CLIENT_TYPE__OPENAI, MODEL_CLIENT_TYPE__TEI]
SUPPORTED_MODEL_CLIENT_TYPES__LANGUAGE = [MODEL_CLIENT_TYPE__OPENAI, MODEL_CLIENT_TYPE__VLLM]
SUPPORTED_MODEL_CLIENT_TYPES__RERANK = [MODEL_CLIENT_TYPE__TEI]
SUPPORTED_MODEL_CLIENT_TYPES__AUDIO = [MODEL_CLIENT_TYPE__OPENAI]

ROUTER_STRATEGY__SHUFFLE = "shuffle"
ROUTER_STRATEGY__ROUND_ROBIN = "round_robin"

CHUNKERS = ["LangchainRecursiveCharacterTextSplitter", "NoChunker"]
DEFAULT_CHUNKER = "LangchainRecursiveCharacterTextSplitter"  # TODO: rename RecursiveCharacterTextSplitter and remove from variables ?

FILE_TYPE__PDF = "application/pdf"
FILE_TYPE__JSON = "application/json"
FILE_TYPE__TXT = "text/plain"
FILE_TYPE__HTML = "text/html"
FILE_TYPE__MD = "text/markdown"
# @TODO : add DOCX_TYPE (application/vnd.openxmlformats-officedocument.wordprocessingml.document)
