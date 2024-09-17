import os

BASE_URL = os.getenv("BASE_URL", "http://localhost:8080/v1")
EMBEDDINGS_MODEL_TYPE = "text-embeddings-inference"
LANGUAGE_MODEL_TYPE = "text-generation"
PRIVATE_COLLECTION_TYPE = "private"
LOCAL_STORAGE_KEY = "albertApiKey"
