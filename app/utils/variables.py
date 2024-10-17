INTERNET_COLLECTION_ID = "internet"
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

USER_ROLE = "user"

HYBRID_SEARCH_TYPE = "hybrid"
LEXICAL_SEARCH_TYPE = "lexical"
SEMANTIC_SEARCH_TYPE = "semantic"
