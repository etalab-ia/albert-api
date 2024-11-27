from fastapi import FastAPI, Response, Security


from slowapi.middleware import SlowAPIASGIMiddleware

from app.endpoints import audio, chat, chunks, collections, completions, documents, embeddings, files, models, search
from app.helpers import ContentSizeLimitMiddleware
from app.schemas.security import User
from app.utils.settings import settings
from app.utils.lifespan import lifespan
from app.utils.security import check_api_key


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=settings.app_description,
    contact={"url": settings.app_contact_url, "email": settings.app_contact_email},
    licence_info={"name": "MIT License", "identifier": "MIT"},
    lifespan=lifespan,
    docs_url="/swagger",
    redoc_url="/documentation",
)

# Middlewares
app.add_middleware(middleware_class=ContentSizeLimitMiddleware)
app.add_middleware(middleware_class=SlowAPIASGIMiddleware)


# Monitoring
@app.get(path="/health", tags=["Monitoring"])
def health(user: User = Security(dependency=check_api_key)) -> Response:
    """
    Health check.
    """

    return Response(status_code=200)


# Core
app.include_router(router=models.router, tags=["Core"], prefix="/v1")
app.include_router(router=chat.router, tags=["Core"], prefix="/v1")
app.include_router(router=completions.router, tags=["Core"], prefix="/v1")
app.include_router(router=embeddings.router, tags=["Core"], prefix="/v1")
app.include_router(router=audio.router, tags=["Core"], prefix="/v1")

# RAG
app.include_router(router=search.router, tags=["Retrieval Augmented Generation"], prefix="/v1")
app.include_router(router=collections.router, tags=["Retrieval Augmented Generation"], prefix="/v1")
app.include_router(router=files.router, tags=["Retrieval Augmented Generation"], prefix="/v1")
app.include_router(router=documents.router, tags=["Retrieval Augmented Generation"], prefix="/v1")
app.include_router(router=chunks.router, tags=["Retrieval Augmented Generation"], prefix="/v1")
