from fastapi import Depends, FastAPI, Response, Security
from prometheus_fastapi_instrumentator import Instrumentator

from app.endpoints import audio, auth, chat, chunks, collections, completions, documents, embeddings, files, models, rerank, search
from app.helpers import Authorization, UsagesMiddleware
from app.schemas.auth import PermissionType
from app.sql.session import get_db
from app.utils.lifespan import lifespan
from app.utils.settings import settings
from app.utils.variables import (
    ROUTER__AUDIO,
    ROUTER__AUTH,
    ROUTER__CHAT,
    ROUTER__CHUNKS,
    ROUTER__COLLECTIONS,
    ROUTER__COMPLETIONS,
    ROUTER__DOCUMENTS,
    ROUTER__EMBEDDINGS,
    ROUTER__FILES,
    ROUTER__MODELS,
    ROUTER__MONITORING,
    ROUTER__RERANK,
    ROUTER__SEARCH,
)


def create_app(*, db_func=get_db, disabled_middleware=False) -> FastAPI:
    """Create FastAPI application."""
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

    if not disabled_middleware:
        # Middlewares
        app.add_middleware(middleware_class=UsagesMiddleware, db_func=db_func)
        app.instrumentator = Instrumentator().instrument(app=app)

    if ROUTER__MONITORING not in settings.disabled_routers:
        app.instrumentator.expose(app=app, should_gzip=True, tags=[ROUTER__MONITORING], dependencies=[Depends(dependency=Authorization(permissions=[PermissionType.READ_METRIC]))], include_in_schema=settings.log_level == "DEBUG")  # fmt: off

        @app.get(path="/health", tags=[ROUTER__MONITORING], include_in_schema=settings.log_level == "DEBUG", dependencies=[Security(dependency=Authorization())])  # fmt: off
        def health() -> Response:
            return Response(status_code=200)

    if ROUTER__COMPLETIONS not in settings.disabled_routers:  # fmt: off
        app.include_router(router=completions.router, tags=[ROUTER__COMPLETIONS], prefix="/v1")
    if ROUTER__EMBEDDINGS not in settings.disabled_routers:  # fmt: off
        app.include_router(router=embeddings.router, tags=[ROUTER__EMBEDDINGS], prefix="/v1")
    if ROUTER__AUDIO not in settings.disabled_routers:  # fmt: off
        app.include_router(router=audio.router, tags=[ROUTER__AUDIO], prefix="/v1")
    if ROUTER__RERANK not in settings.disabled_routers:  # fmt: off
        app.include_router(router=rerank.router, tags=[ROUTER__RERANK], prefix="/v1")
    if ROUTER__MODELS not in settings.disabled_routers:  # fmt: off
        app.include_router(router=models.router, tags=[ROUTER__MODELS], prefix="/v1")
    if ROUTER__AUTH not in settings.disabled_routers:  # fmt: off
        app.include_router(router=auth.router, tags=[ROUTER__AUTH], include_in_schema=settings.log_level == "DEBUG")
    if ROUTER__CHAT not in settings.disabled_routers:  # fmt: off
        app.include_router(router=chat.router, tags=[ROUTER__CHAT], prefix="/v1")
    if ROUTER__SEARCH not in settings.disabled_routers:  # fmt: off
        app.include_router(router=search.router, tags=[ROUTER__SEARCH], prefix="/v1")
    if ROUTER__COLLECTIONS not in settings.disabled_routers:  # fmt: off
        app.include_router(router=collections.router, tags=[ROUTER__COLLECTIONS], prefix="/v1")
    if ROUTER__FILES not in settings.disabled_routers:  # fmt: off
        app.include_router(router=files.router, tags=[ROUTER__FILES], prefix="/v1")
    if ROUTER__DOCUMENTS not in settings.disabled_routers:  # fmt: off
        app.include_router(router=documents.router, tags=[ROUTER__DOCUMENTS], prefix="/v1")
    if ROUTER__CHUNKS not in settings.disabled_routers:  # fmt: off
        app.include_router(router=chunks.router, tags=[ROUTER__CHUNKS], prefix="/v1")
