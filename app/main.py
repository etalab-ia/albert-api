import logging

from fastapi import APIRouter, Depends, FastAPI, Request, Response, Security
from fastapi.dependencies.utils import get_dependant
from prometheus_fastapi_instrumentator import Instrumentator
import sentry_sdk

from app.endpoints import audio, auth, chat, chunks, collections, completions, documents, embeddings, files, models, ocr, parse, rerank, search, mcp
from app.helpers._accesscontroller import AccessController
from app.schemas.auth import PermissionType
from app.schemas.core.context import RequestContext
from app.schemas.usage import Usage
from app.utils.context import generate_request_id, request_context
from app.utils.hooks_decorator import hooks
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
    ROUTER__OCR,
    ROUTER__PARSE,
    ROUTER__RERANK,
    ROUTER__SEARCH,
    ROUTER__MCP,
)

logger = logging.getLogger(__name__)

if settings.monitoring.sentry is not None and settings.monitoring.sentry.enabled:
    logger.info("Initializing Sentry SDK.")
    sentry_sdk.init(**settings.monitoring.sentry.model_dump())


def create_app(*args, **kwargs) -> FastAPI:
    """Create FastAPI application."""

    def add_hooks(router: APIRouter) -> None:
        for route in router.routes:
            route.endpoint = hooks(route.endpoint)
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
        request_context.set(
            RequestContext(
                id=generate_request_id(),
                method=request.method,
                endpoint=request.url.path,
                client=request.client.host,
                usage=Usage(),
            )
        )

        return await call_next(request)

    # Routers

    if ROUTER__AUDIO not in settings.general.disabled_routers:
        add_hooks(router=audio.router)
        app.include_router(router=audio.router, tags=[ROUTER__AUDIO.title()], prefix="/v1")

    if ROUTER__AUTH not in settings.general.disabled_routers:
        add_hooks(router=auth.router)
        app.include_router(router=auth.router, tags=[ROUTER__AUTH.title()])

    if ROUTER__CHAT not in settings.general.disabled_routers:
        add_hooks(router=chat.router)
        app.include_router(router=chat.router, tags=[ROUTER__CHAT.title()], prefix="/v1")

    if ROUTER__CHUNKS not in settings.general.disabled_routers:
        add_hooks(router=chunks.router)
        app.include_router(router=chunks.router, tags=[ROUTER__CHUNKS.title()], prefix="/v1")

    if ROUTER__COLLECTIONS not in settings.general.disabled_routers:
        add_hooks(router=collections.router)
        app.include_router(router=collections.router, tags=[ROUTER__COLLECTIONS.title()], prefix="/v1")

    if ROUTER__DOCUMENTS not in settings.general.disabled_routers:
        add_hooks(router=documents.router)
        app.include_router(router=documents.router, tags=[ROUTER__DOCUMENTS.title()], prefix="/v1")

    if ROUTER__EMBEDDINGS not in settings.general.disabled_routers:
        add_hooks(router=embeddings.router)
        app.include_router(router=embeddings.router, tags=[ROUTER__EMBEDDINGS.title()], prefix="/v1")

    if ROUTER__MODELS not in settings.general.disabled_routers:
        add_hooks(router=models.router)
        app.include_router(router=models.router, tags=[ROUTER__MODELS.title()], prefix="/v1")

    if ROUTER__MONITORING not in settings.general.disabled_routers:
        if settings.monitoring.prometheus is not None and settings.monitoring.prometheus.enabled is True:
            app.instrumentator = Instrumentator().instrument(app=app)
            app.instrumentator.expose(app=app, should_gzip=True, tags=[ROUTER__MONITORING.title()], dependencies=[Depends(dependency=AccessController(permissions=[PermissionType.READ_METRIC]))], include_in_schema=settings.general.log_level == "DEBUG")  # fmt: off

        @app.get(path="/health", tags=[ROUTER__MONITORING.title()], include_in_schema=settings.general.log_level == "DEBUG", dependencies=[Security(dependency=AccessController())])  # fmt: off
        def health() -> Response:
            return Response(status_code=200)

    if ROUTER__MCP not in settings.general.disabled_routers:
        add_hooks(router=mcp.router)
        app.include_router(router=mcp.router, tags=[ROUTER__MCP.upper()], prefix="/v1")

    if ROUTER__OCR not in settings.general.disabled_routers:
        add_hooks(router=ocr.router)
        app.include_router(router=ocr.router, tags=[ROUTER__OCR.upper()], prefix="/v1")

    if ROUTER__PARSE not in settings.general.disabled_routers:
        add_hooks(router=parse.router)
        app.include_router(router=parse.router, tags=[ROUTER__PARSE.title()], prefix="/v1")

    if ROUTER__RERANK not in settings.general.disabled_routers:
        add_hooks(router=rerank.router)
        app.include_router(router=rerank.router, tags=[ROUTER__RERANK.title()], prefix="/v1")

    if ROUTER__SEARCH not in settings.general.disabled_routers:
        add_hooks(router=search.router)
        app.include_router(router=search.router, tags=[ROUTER__SEARCH.title()], prefix="/v1")

    # DEPRECATED LEGACY ENDPOINTS
    if ROUTER__COMPLETIONS not in settings.general.disabled_routers:
        add_hooks(router=completions.router)
        app.include_router(router=completions.router, tags=["Legacy"], prefix="/v1")

    if ROUTER__FILES not in settings.general.disabled_routers:
        # hooks does not work with files endpoint (request is overwritten by the file upload)
        app.include_router(router=files.router, tags=["Legacy"], prefix="/v1")

    return app


app = create_app()
