from fastapi import FastAPI, Response, Security


from slowapi.middleware import SlowAPIASGIMiddleware

from app.endpoints import audio, chat, chunks, collections, completions, documents, embeddings, files, models, search
from app.helpers import ContentSizeLimitMiddleware
from app.schemas.security import User
from app.utils.config import APP_CONTACT_EMAIL, APP_CONTACT_URL, APP_DESCRIPTION, APP_VERSION
from app.utils.lifespan import lifespan
from app.utils.security import check_api_key


app = FastAPI(
    title="Albert API",
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    contact={"url": APP_CONTACT_URL, "email": APP_CONTACT_EMAIL},
    licence_info={"name": "MIT License", "identifier": "MIT"},
    lifespan=lifespan,
    docs_url="/swagger",
    redoc_url="/documentation",
)

# Middlewares
app.add_middleware(ContentSizeLimitMiddleware)
app.add_middleware(SlowAPIASGIMiddleware)


# Monitoring
@app.get("/health", tags=["Monitoring"])
def health(user: User = Security(check_api_key)):
    """
    Health check.
    """

    return Response(status_code=200)


# Core
app.include_router(models.router, tags=["Core"], prefix="/v1")
app.include_router(chat.router, tags=["Core"], prefix="/v1")
app.include_router(completions.router, tags=["Core"], prefix="/v1")
app.include_router(embeddings.router, tags=["Core"], prefix="/v1")
app.include_router(audio.router, tags=["Core"], prefix="/v1")

# RAG
app.include_router(search.router, tags=["Retrieval Augmented Generation"], prefix="/v1")
app.include_router(collections.router, tags=["Retrieval Augmented Generation"], prefix="/v1")
app.include_router(files.router, tags=["Retrieval Augmented Generation"], prefix="/v1")
app.include_router(documents.router, tags=["Retrieval Augmented Generation"], prefix="/v1")
app.include_router(chunks.router, tags=["Retrieval Augmented Generation"], prefix="/v1")
