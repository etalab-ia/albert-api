AUDIO_MODEL_TYPE = "automatic-speech-recognition"
INTERNET_COLLECTION_DISPLAY_ID = "internet"
PUBLIC_COLLECTION_TYPE = "public"
PRIVATE_COLLECTION_TYPE = "private"

EMBEDDINGS_MODEL_TYPE = "text-embeddings-inference"
LANGUAGE_MODEL_TYPE = "text-generation"

CHUNKERS = ["LangchainRecursiveCharacterTextSplitter", "NoChunker"]
DEFAULT_CHUNKER = "LangchainRecursiveCharacterTextSplitter"

PDF_TYPE = "application/pdf"
JSON_TYPE = "application/json"
TXT_TYPE = "text/plain"
HTML_TYPE = "text/html"

# @TODO : add DOCX_TYPE (application/vnd.openxmlformats-officedocument.wordprocessingml.document)
ROLE_LEVEL_0 = 0
ROLE_LEVEL_1 = 1
ROLE_LEVEL_2 = 2
USER_ROLE = "user"

INTERNET_DUCKDUCKGO_TYPE = "duckduckgo"
INTERNET_BRAVE_TYPE = "brave"

# Clients
SEARCH_CLIENT_ELASTIC_TYPE = "elastic"
SEARCH_CLIENT_QDRANT_TYPE = "qdrant"
INTERNET_CLIENT_BRAVE_TYPE = "brave"
INTERNET_CLIENT_DUCKDUCKGO_TYPE = "duckduckgo"

# RAG parameters
DEFAULT_RAG_TEMPLATE = "Réponds à la question suivante en te basant sur les documents ci-dessous : {prompt}\n\nDocuments :\n{chunks}"

HYBRID_SEARCH_TYPE = "hybrid"
LEXICAL_SEARCH_TYPE = "lexical"
SEMANTIC_SEARCH_TYPE = "semantic"

DEFAULT_TIMEOUT = 120
