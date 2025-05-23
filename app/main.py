import logging

from fastapi import APIRouter, Depends, FastAPI, Request, Response, Security
from fastapi.dependencies.utils import get_dependant
from prometheus_fastapi_instrumentator import Instrumentator
import sentry_sdk

from app.endpoints import audio, auth, chat, chunks, collections, completions, documents, embeddings, files, models, ocr, rerank, search
from app.helpers import AccessController
from app.schemas.auth import PermissionType
from app.schemas.core.context import RequestContext
from app.schemas.usage import Usage
from app.sql.session import get_db
from app.utils.context import request_context
from app.utils.lifespan import lifespan
from app.utils.settings import settings
from app.utils.usage_decorator import log_usage
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
    ROUTER__OCR,
    ROUTER__RERANK,
    ROUTER__SEARCH,
)

logger = logging.getLogger(__name__)

if settings.general.sentry_dsn:
    # If SENTRY_DSN is set, we initialize Sentry SDK
    # This is useful for error tracking and performance monitoring
    # See https://docs.sentry.io/platforms/python/guides/fastapi/
    # for more information on how to configure Sentry with FastAPI
    sentry_sdk.init(
        dsn=settings.general.sentry_dsn,
        # See https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
        send_default_pii=True,
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for tracing.
        traces_sample_rate=1.0,
        # Set profile_session_sample_rate to 1.0 to profile 100%
        # of profile sessions.
        profile_session_sample_rate=1.0,
        # Set profile_lifecycle to "trace" to automatically
        # run the profiler on when there is an active transaction
        profile_lifecycle="trace",
    )
else:
    logger.warning("SENTRY_DSN is not set. Sentry SDK will not be initialized.")


def create_app(db_func=get_db, *args, **kwargs) -> FastAPI:
    """Create FastAPI application."""

    def add_usage_decorator(router: APIRouter):
        for route in router.routes:
            route.endpoint = log_usage(route.endpoint)
            route.dependant = get_dependant(path=route.path_format, call=route.endpoint)

    app = FastAPI(
        title=settings.general.title,
        summary=settings.general.summary,
        version=settings.general.version,
        description=settings.general.description,
        terms_of_service=settings.general.terms_of_service,
        contact={"name": settings.general.contact_name, "url": settings.general.contact_url, "email": settings.general.contact_email},
        licence_info={"name": settings.general.licence_name, "identifier": settings.general.licence_identifier, "url": settings.general.licence_url},
        lifespan=lifespan,
        docs_url=settings.general.docs_url,
        redoc_url=settings.general.redoc_url,
    )

    @app.middleware("http")
    async def set_request_context(request: Request, call_next):
        """Middleware to set request context."""
        request_context.set(RequestContext(method=request.method, path=request.url.path, client=request.client.host, usage=Usage()))

        return await call_next(request)

    # Routers
    if ROUTER__AUDIO not in settings.general.disabled_routers:
        if ROUTER__AUDIO in settings.usages.routers:
            add_usage_decorator(router=audio.router)
        app.include_router(router=audio.router, tags=[ROUTER__AUDIO.title()], prefix="/v1")

    if ROUTER__AUTH not in settings.general.disabled_routers:
        if ROUTER__AUTH in settings.usages.routers:
            add_usage_decorator(router=auth.router)
        app.include_router(router=auth.router, tags=[ROUTER__AUTH.title()])

    if ROUTER__CHAT not in settings.general.disabled_routers:
        if ROUTER__CHAT in settings.usages.routers:
            add_usage_decorator(router=chat.router)
        app.include_router(router=chat.router, tags=[ROUTER__CHAT.title()], prefix="/v1")

    if ROUTER__CHUNKS not in settings.general.disabled_routers:
        if ROUTER__CHUNKS in settings.usages.routers:
            add_usage_decorator(router=chunks.router)
        app.include_router(router=chunks.router, tags=[ROUTER__CHUNKS.title()], prefix="/v1")

    if ROUTER__COLLECTIONS not in settings.general.disabled_routers:
        if ROUTER__COLLECTIONS in settings.usages.routers:
            add_usage_decorator(router=collections.router)
        app.include_router(router=collections.router, tags=[ROUTER__COLLECTIONS.title()], prefix="/v1")

    if ROUTER__COMPLETIONS not in settings.general.disabled_routers:
        if ROUTER__COMPLETIONS in settings.usages.routers:
            add_usage_decorator(router=completions.router)
        app.include_router(router=completions.router, tags=[ROUTER__COMPLETIONS.title()], prefix="/v1")

    if ROUTER__DOCUMENTS not in settings.general.disabled_routers:
        if ROUTER__DOCUMENTS in settings.usages.routers:
            add_usage_decorator(router=documents.router)
        app.include_router(router=documents.router, tags=[ROUTER__DOCUMENTS.title()], prefix="/v1")

    if ROUTER__EMBEDDINGS not in settings.general.disabled_routers:
        if ROUTER__EMBEDDINGS in settings.usages.routers:
            add_usage_decorator(router=embeddings.router)
        app.include_router(router=embeddings.router, tags=[ROUTER__EMBEDDINGS.title()], prefix="/v1")

    if ROUTER__FILES not in settings.general.disabled_routers:
        if ROUTER__FILES in settings.usages.routers:
            add_usage_decorator(router=files.router)
        app.include_router(router=files.router, tags=[ROUTER__FILES.title()], prefix="/v1")

    if ROUTER__MODELS not in settings.general.disabled_routers:
        if ROUTER__MODELS in settings.usages.routers:
            add_usage_decorator(router=models.router)
        app.include_router(router=models.router, tags=[ROUTER__MODELS.title()], prefix="/v1")

    if ROUTER__MONITORING not in settings.general.disabled_routers:
        app.instrumentator = Instrumentator().instrument(app=app)
        app.instrumentator.expose(app=app, should_gzip=True, tags=[ROUTER__MONITORING.title()], dependencies=[Depends(dependency=AccessController(permissions=[PermissionType.READ_METRIC]))], include_in_schema=settings.general.log_level == "DEBUG")  # fmt: off

        @app.get(path="/health", tags=[ROUTER__MONITORING.title()], include_in_schema=settings.general.log_level == "DEBUG", dependencies=[Security(dependency=AccessController())])  # fmt: off
        def health() -> Response:
            return Response(status_code=200)

    if ROUTER__OCR not in settings.general.disabled_routers:
        if ROUTER__OCR in settings.usages.routers:
            add_usage_decorator(router=ocr.router)
        app.include_router(router=ocr.router, tags=[ROUTER__OCR.upper()], prefix="/v1")

    if ROUTER__RERANK not in settings.general.disabled_routers:
        if ROUTER__RERANK in settings.usages.routers:
            add_usage_decorator(router=rerank.router)
        app.include_router(router=rerank.router, tags=[ROUTER__RERANK.title()], prefix="/v1")

    if ROUTER__SEARCH not in settings.general.disabled_routers:
        if ROUTER__SEARCH in settings.usages.routers:
            add_usage_decorator(router=search.router)
        app.include_router(router=search.router, tags=[ROUTER__SEARCH.title()], prefix="/v1")

    return app


app = create_app(db_func=get_db)
