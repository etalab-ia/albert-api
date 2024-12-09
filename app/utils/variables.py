DEFAULT_TIMEOUT = 120

INTERNET_COLLECTION_DISPLAY_ID = "internet"

HYBRID_SEARCH_TYPE = "hybrid"
LEXICAL_SEARCH_TYPE = "lexical"
SEMANTIC_SEARCH_TYPE = "semantic"

PUBLIC_COLLECTION_TYPE = "public"
PRIVATE_COLLECTION_TYPE = "private"

AUDIO_MODEL_TYPE = "automatic-speech-recognition"
EMBEDDINGS_MODEL_TYPE = "text-embeddings-inference"
LANGUAGE_MODEL_TYPE = "text-generation"

CHUNKERS = ["LangchainRecursiveCharacterTextSplitter", "NoChunker"]
DEFAULT_CHUNKER = "LangchainRecursiveCharacterTextSplitter"

PDF_TYPE = "application/pdf"
JSON_TYPE = "application/json"
TXT_TYPE = "text/plain"
HTML_TYPE = "text/html"
MARKDOWN_TYPE = "text/markdown"
# @TODO : add DOCX_TYPE (application/vnd.openxmlformats-officedocument.wordprocessingml.document)

# Clients
SEARCH_CLIENT_ELASTIC_TYPE = "elastic"
SEARCH_CLIENT_QDRANT_TYPE = "qdrant"
INTERNET_CLIENT_BRAVE_TYPE = "brave"
INTERNET_CLIENT_DUCKDUCKGO_TYPE = "duckduckgo"
