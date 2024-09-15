import os

BASE_URL = os.getenv("BASE_URL", "http://localhost:8080/v1")
DEFAULT_COLLECTION = "Mes documents"
EMBEDDINGS_MODEL_TYPE = "text-embeddings-inference"
LANGUAGE_MODEL_TYPE = "text-generation"
PRIVATE_COLLECTION_TYPE = "private"
