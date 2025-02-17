from fastapi import Depends, FastAPI, Response, Security
from prometheus_fastapi_instrumentator import Instrumentator

from app.endpoints import audio, chat, chunks, collections, completions, documents, embeddings, files, models, rerank, search
from app.helpers import MetricsMiddleware
from app.schemas.security import User
from app.utils.lifespan import lifespan
from app.utils.security import check_admin_api_key, check_api_key
from app.utils.settings import settings

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

# Prometheus metrics
app.instrumentator = Instrumentator().instrument(app=app)

# Middlewares
# app.add_middleware(middleware_class=SlowAPIASGIMiddleware)
app.add_middleware(middleware_class=MetricsMiddleware)


# Monitoring
@app.get(path="/health", tags=["Monitoring"])
def health(user: User = Security(dependency=check_api_key)) -> Response:
    """
    Health check.
    """

    return Response(status_code=200)


app.instrumentator.expose(app=app, should_gzip=True, tags=["Monitoring"], dependencies=[Depends(dependency=check_admin_api_key)])

app.include_router(router=models.router, tags=["Models"], prefix="/v1")
app.include_router(router=chat.router, tags=["Chat"], prefix="/v1")
app.include_router(router=completions.router, tags=["Completions"], prefix="/v1")
app.include_router(router=embeddings.router, tags=["Embeddings"], prefix="/v1")
app.include_router(router=audio.router, tags=["Audio"], prefix="/v1")
app.include_router(router=rerank.router, tags=["Reranking"], prefix="/v1")
app.include_router(router=search.router, tags=["Search"], prefix="/v1")
app.include_router(router=collections.router, tags=["Collections"], prefix="/v1")
app.include_router(router=files.router, tags=["Files"], prefix="/v1")
app.include_router(router=documents.router, tags=["Documents"], prefix="/v1")
app.include_router(router=chunks.router, tags=["Chunks"], prefix="/v1")
